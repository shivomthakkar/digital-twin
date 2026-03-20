from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict
import json
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from context import prompt

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

if AWS_PROFILE_NAME := os.getenv("AWS_PROFILE_NAME"):
    boto3.setup_default_session(profile_name=AWS_PROFILE_NAME)

bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.getenv("AWS_REGION_NAME", "us-east-1"),
)
lambda_client = boto3.client("lambda")
ses_client = boto3.client(
    "ses",
    region_name=os.getenv("SES_REGION", os.getenv("AWS_REGION_NAME", "us-east-1")),
)

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0")

# Memory storage configuration
USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "")
MEMORY_DIR = os.getenv("MEMORY_DIR", "../memory")

# Tool configuration
TRADING_LAMBDA_FUNCTION_NAME = os.getenv("TRADING_LAMBDA_FUNCTION_NAME", "")
TRADING_USER_ID = os.getenv("TRADING_USER_ID", "")
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")

# Initialize S3 client if needed
if USE_S3:
    s3_client = boto3.client("s3")

# ---------------------------------------------------------------------------
# Bedrock tool definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "toolSpec": {
            "name": "get_holdings",
            "description": (
                "Retrieve all current stock holdings from the trading account. "
                "Returns each holding's symbol, quantity, average cost, current price, "
                "P&L, and a portfolio summary."
            ),
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
    {
        "toolSpec": {
            "name": "get_positions",
            "description": (
                "Retrieve all currently open intraday and short-term trading positions "
                "with unrealized P&L per position and a total unrealized P&L summary."
            ),
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
    {
        "toolSpec": {
            "name": "get_pnl",
            "description": (
                "Calculate realized and unrealized profit/loss for a given time period. "
                "Returns gross P&L, charges, net P&L, trade statistics, and current unrealized P&L."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["week", "2weeks", "month"],
                            "description": "Time period for P&L calculation.",
                        }
                    },
                    "required": ["period"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_funds",
            "description": (
                "Retrieve trading account balances, margin utilization, blocked amounts, "
                "and other fund details."
            ),
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
    {
        "toolSpec": {
            "name": "send_email_notification",
            "description": (
                "Send an email notification to the account owner. "
                "Use this when a visitor asks something you cannot answer or do not know, "
                "when a request is outside your scope, or when you want to flag something "
                "important to the owner. Always include the original user message in the body."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Concise email subject line.",
                        },
                        "body": {
                            "type": "string",
                            "description": (
                                "Email body. Include the visitor's original message "
                                "and relevant context."
                            ),
                        },
                    },
                    "required": ["subject", "body"],
                }
            },
        }
    },
]

TOOL_CONFIG = {"tools": TOOL_DEFINITIONS}


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class Message(BaseModel):
    role: str
    content: str
    timestamp: str


# Memory management functions
def get_memory_path(session_id: str) -> str:
    return f"{session_id}.json"


def load_conversation(session_id: str) -> List[Dict]:
    """Load conversation history from storage"""
    if USE_S3:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=get_memory_path(session_id))
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return []
            raise
    else:
        # Local file storage
        file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return []


def save_conversation(session_id: str, messages: List[Dict]):
    """Save conversation history to storage"""
    if USE_S3:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=get_memory_path(session_id),
            Body=json.dumps(messages, indent=2),
            ContentType="application/json",
        )
    else:
        # Local file storage
        os.makedirs(MEMORY_DIR, exist_ok=True)
        file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
        with open(file_path, "w") as f:
            json.dump(messages, f, indent=2)

def call_bedrock_with_tools(conversation: List[Dict], user_message: str) -> str:
    """Agentic Bedrock loop with tool use support."""

    # Build messages from conversation history (backward-compat: content may be str or list)
    messages: List[Dict] = []
    for msg in conversation[-50:]:
        content = msg["content"]
        if isinstance(content, str):
            content = [{"text": content}]
        messages.append({"role": msg["role"], "content": content})

    messages.append({"role": "user", "content": [{"text": user_message}]})

    max_iterations = 10
    for _ in range(max_iterations):
        try:
            response = bedrock_client.converse(
                modelId=BEDROCK_MODEL_ID,
                system=[{"text": prompt()}],
                messages=messages,
                toolConfig=TOOL_CONFIG,
                inferenceConfig={"maxTokens": 2000, "temperature": 0.7, "topP": 0.9},
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ValidationException":
                print(f"Bedrock validation error: {e}")
                raise HTTPException(status_code=400, detail="Invalid message format for Bedrock")
            elif error_code == "AccessDeniedException":
                print(f"Bedrock access denied: {e}")
                raise HTTPException(status_code=403, detail="Access denied to Bedrock model")
            else:
                print(f"Bedrock error: {e}")
                raise HTTPException(status_code=500, detail=f"Bedrock error: {str(e)}")

        stop_reason = response["stopReason"]
        assistant_message = response["output"]["message"]

        if stop_reason == "end_turn":
            return " ".join(
                block["text"]
                for block in assistant_message["content"]
                if "text" in block
            )

        if stop_reason == "tool_use":
            messages.append(assistant_message)

            tool_results = []
            for block in assistant_message["content"]:
                if "toolUse" not in block:
                    continue
                tool_use = block["toolUse"]
                tool_use_id = tool_use["toolUseId"]
                tool_name = tool_use["name"]
                tool_input = tool_use.get("input", {})
                print(f"[tool] {tool_name}({json.dumps(tool_input)})")
                try:
                    result = _execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"json": result}],
                            "status": "success",
                        }
                    })
                except Exception as exc:
                    print(f"[tool error] {tool_name}: {exc}")
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"text": f"Error: {exc}"}],
                            "status": "error",
                        }
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason — return whatever text is available
        print(f"Unexpected stop reason: {stop_reason}")
        break

    # Fallback: extract text from the last assistant turn if present
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            text_blocks = [b["text"] for b in msg.get("content", []) if "text" in b]
            if text_blocks:
                return " ".join(text_blocks)

    return "I encountered an unexpected issue processing your request."


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _invoke_trading_lambda(
    method: str,
    path: str,
    body: Optional[Dict] = None,
    query_params: Optional[Dict] = None,
) -> Dict:
    """Invoke the trading Lambda directly with a synthetic API GW HTTP v2 event."""
    if not TRADING_LAMBDA_FUNCTION_NAME:
        raise ValueError("TRADING_LAMBDA_FUNCTION_NAME is not configured")
    if not TRADING_USER_ID:
        raise ValueError("TRADING_USER_ID is not configured")

    raw_query = "&".join(f"{k}={v}" for k, v in (query_params or {}).items())

    event = {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": raw_query,
        "headers": {"content-type": "application/json"},
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "digital-twin-internal",
            },
            "authorizer": {"claims": {"sub": TRADING_USER_ID}},
        },
        "body": json.dumps(body) if body else None,
        "isBase64Encoded": False,
    }

    raw_response = lambda_client.invoke(
        FunctionName=TRADING_LAMBDA_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(event).encode("utf-8"),
    )
    payload = json.loads(raw_response["Payload"].read())
    status_code = payload.get("statusCode", 500)

    response_body = payload.get("body")
    if isinstance(response_body, str):
        response_body = json.loads(response_body)
    response_body = response_body or {}

    if status_code >= 400:
        raise ValueError(
            f"Trading API error {status_code}: {response_body.get('error', 'Unknown error')}"
        )

    return response_body


def _send_ses_email(subject: str, body_text: str) -> Dict:
    """Send an email notification via AWS SES."""
    if not SES_SENDER_EMAIL or not NOTIFICATION_EMAIL:
        print("SES not configured — skipping email")
        return {"status": "skipped", "reason": "SES_SENDER_EMAIL or NOTIFICATION_EMAIL not set"}

    try:
        ses_client.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={"ToAddresses": [NOTIFICATION_EMAIL]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
            },
        )
        return {"status": "sent", "to": NOTIFICATION_EMAIL}
    except ClientError as exc:
        print(f"SES error: {exc}")
        return {"status": "error", "reason": str(exc)}


def _execute_tool(tool_name: str, tool_input: Dict) -> Dict:
    """Route a tool call to the appropriate handler."""
    if tool_name == "get_holdings":
        return _invoke_trading_lambda("GET", "/holdings")
    if tool_name == "get_positions":
        return _invoke_trading_lambda("GET", "/positions")
    if tool_name == "get_pnl":
        period = tool_input.get("period", "week")
        return _invoke_trading_lambda("GET", "/pnl", query_params={"period": period})
    if tool_name == "get_funds":
        return _invoke_trading_lambda("GET", "/funds")
    if tool_name == "send_email_notification":
        return _send_ses_email(tool_input["subject"], tool_input["body"])
    raise ValueError(f"Unknown tool: {tool_name}")


@app.get("/")
async def root():
    return {
        "message": "AI Digital Twin API (Powered by AWS Bedrock)",
        "memory_enabled": True,
        "storage": "S3" if USE_S3 else "local",
        "ai_model": BEDROCK_MODEL_ID,
        "tools_enabled": bool(TRADING_LAMBDA_FUNCTION_NAME and TRADING_USER_ID),
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "use_s3": USE_S3,
        "bedrock_model": BEDROCK_MODEL_ID
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Load conversation history
        conversation = load_conversation(session_id)

        # Call Bedrock for response
        assistant_response = call_bedrock_with_tools(conversation, request.message)

        # Update conversation history
        conversation.append(
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
        )
        conversation.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Save conversation
        save_conversation(session_id, conversation)

        return ChatResponse(response=assistant_response, session_id=session_id)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Retrieve conversation history"""
    try:
        conversation = load_conversation(session_id)
        return {"session_id": session_id, "messages": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)