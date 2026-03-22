from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict, Tuple
import json
import uuid
import re
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import httpx
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
TRADING_API_URL = os.getenv("TRADING_API_URL", "")  # For local dev: http://localhost:8001
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
DEV_USER_ID = os.getenv("DEV_USER_ID", "")

# Initialize S3 client if needed
if USE_S3:
    s3_client = boto3.client("s3")

# ---------------------------------------------------------------------------
# Bedrock tool definitions — composed per-request based on context
# ---------------------------------------------------------------------------

_TRADING_TOOLS = [
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
            "name": "list_orders",
            "description": (
                "Retrieve all orders for the current trading session. "
                "Returns order details including symbol, quantity, price, status, and timestamps."
            ),
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
    {
        "toolSpec": {
            "name": "get_order",
            "description": (
                "Retrieve details of a specific order by order ID. "
                "Returns full order information including fills and execution details."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The unique order ID.",
                        }
                    },
                    "required": ["order_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "place_order",
            "description": (
                "Place a new market or limit order. Always confirm with the user before executing. "
                "Pass the complete order specification."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol (e.g., INFY, TCS)."},
                        "qty": {"type": "integer", "description": "Quantity to trade."},
                        "side": {"type": "string", "enum": ["BUY", "SELL"], "description": "Buy or Sell."},
                        "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "description": "Order type."},
                        "price": {"type": "number", "description": "Limit price (required for LIMIT orders)."},
                    },
                    "required": ["symbol", "qty", "side", "order_type"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "modify_order",
            "description": (
                "Modify an existing pending order. Can change quantity and price. "
                "Always confirm with the user before executing."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The unique order ID to modify."},
                        "qty": {"type": "integer", "description": "New quantity (optional)."},
                        "price": {"type": "number", "description": "New limit price (optional)."},
                    },
                    "required": ["order_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "cancel_order",
            "description": (
                "Cancel a pending order. Always confirm with the user before executing."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The unique order ID to cancel."}
                    },
                    "required": ["order_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "list_forever_orders",
            "description": (
                "Retrieve all Good-Till-Cancelled (GTC) / Forever orders (one-cancel-other, etc.). "
                "Returns order details with current status."
            ),
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
    {
        "toolSpec": {
            "name": "place_forever_order",
            "description": (
                "Place a Good-Till-Cancelled (GTC) or advanced forever order (one-cancel-other, bracket, etc.). "
                "Always confirm with the user before executing."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol."},
                        "qty": {"type": "integer", "description": "Quantity."},
                        "side": {"type": "string", "enum": ["BUY", "SELL"], "description": "Buy or Sell."},
                        "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "description": "Order type."},
                        "price": {"type": "number", "description": "Limit price (if LIMIT)."},
                        "order_spec": {"type": "object", "description": "Advanced order parameters (optional)."},
                    },
                    "required": ["symbol", "qty", "side", "order_type"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "modify_forever_order",
            "description": (
                "Modify an existing GTC / Forever order. Always confirm with the user before executing."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The unique forever order ID."},
                        "qty": {"type": "integer", "description": "New quantity (optional)."},
                        "price": {"type": "number", "description": "New limit price (optional)."},
                    },
                    "required": ["order_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "cancel_forever_order",
            "description": (
                "Cancel a GTC / Forever order. Always confirm with the user before executing."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The unique forever order ID."}
                    },
                    "required": ["order_id"],
                }
            },
        }
    },
]

_EMAIL_TOOLS = [
    {
        "toolSpec": {
            "name": "send_email_notification",
            "description": (
                "Send an email notification to the account owner. "
                "Use this when a visitor asks something you cannot answer or do not know, "
                "when a request is outside your scope, or when you want to flag something "
                "important to the owner. Always include the original user message in the body."
                "If you know the visitor's details (name, email), include that in the message as "
                "well so the owner can follow up directly."
                "Avoid reusing this tool for multiple times in the same conversation to prevent spamming."
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


def _build_tool_config(context: str, trading_user_id: Optional[str]) -> Dict:
    """Return the Bedrock toolConfig for the given request context.

    conversation — email notification only.
    trading      — email notification + all trading read tools (requires a resolved user ID).
    """
    tools = list(_EMAIL_TOOLS)
    if context == "trading" and trading_user_id:
        tools.extend(_TRADING_TOOLS)
    return {"tools": tools}


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: str = "conversation"  # "conversation" | "trading"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    options: Optional[List[str]] = None


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


def _extract_user_id(request: Request) -> Optional[str]:
    """Extract the Cognito sub from the Lambda event injected by Mangum.

    Mirrors trading/auth.py::get_current_user but returns None instead of
    raising so callers can decide how to handle the missing identity.
    Falls back to DEV_USER_ID for local development.
    """
    event: dict = request.scope.get("aws.event", {})
    sub: Optional[str] = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
        .get("sub")
    )
    return sub or os.getenv("DEV_USER_ID")


def _extract_user_claims(request: Request) -> Optional[Dict]:
    """Extract all JWT claims from the Lambda event.
    
    Returns the complete claims dict from Cognito authorizer if available,
    otherwise returns None.
    """
    event: dict = request.scope.get("aws.event", {})
    claims: Optional[Dict] = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims")
    )
    return claims


def _extract_quick_options(text: str) -> Tuple[str, Optional[List[str]]]:
    """Strip <thinking> blocks and [QUICK_OPTIONS] markers from LLM output.

    Returns (clean_text, options_list_or_None).
    """
    # Remove <thinking>…</thinking> blocks (extended reasoning / scratchpad)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL).strip()

    match = re.search(r'\[QUICK_OPTIONS\](.*?)\[/QUICK_OPTIONS\]', text, re.DOTALL)
    if not match:
        return text.strip(), None
    options = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    clean_text = re.sub(r'\[QUICK_OPTIONS\].*?\[/QUICK_OPTIONS\]', '', text, flags=re.DOTALL).strip()
    return clean_text, options if options else None


def call_bedrock_with_tools(
    conversation: List[Dict],
    user_message: str,
    tool_config: Dict,
    trading_user_id: Optional[str] = None,
    context: str = "conversation",
    user_claims: Optional[Dict] = None,
) -> Tuple[str, Optional[List[str]]]:
    """Agentic Bedrock loop with tool use support.
    
    Args:
        conversation: List of previous messages in the conversation.
        user_message: The current user message to process.
        tool_config: Tool configuration dict from _build_tool_config().
        trading_user_id: Optional user ID for trading context authentication.
        context: Either "conversation" or "trading", passed to prompt().
        user_claims: Optional JWT claims dict from request authorizer.
    """

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
                system=[{"text": prompt(context=context, trading_user_id=trading_user_id, user_claims=user_claims)}],
                messages=messages,
                toolConfig=tool_config,
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
            raw = " ".join(
                block["text"]
                for block in assistant_message["content"]
                if "text" in block
            )
            return _extract_quick_options(raw)

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
                    result = _execute_tool(tool_name, tool_input, trading_user_id)
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
                return _extract_quick_options(" ".join(text_blocks))

    return "I encountered an unexpected issue processing your request.", None


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _invoke_trading_http(
    method: str,
    path: str,
    trading_user_id: str,
    body: Optional[Dict] = None,
    query_params: Optional[Dict] = None,
) -> Dict:
    """Invoke the trading API via HTTP (local development)."""
    if not TRADING_API_URL:
        raise ValueError("TRADING_API_URL is not configured for HTTP mode")

    url = f"{TRADING_API_URL}{path}"
    headers = {
        "Authorization": f"Bearer dummy-token-for-sub-{trading_user_id}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client() as client:
            if method == "GET":
                response = client.get(url, headers=headers, params=query_params)
            elif method == "POST":
                response = client.post(url, headers=headers, json=body)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code >= 400:
                raise ValueError(
                    f"Trading API error {response.status_code}: {response.text}"
                )
            return response.json()
    except httpx.ConnectError as e:
        raise ValueError(f"Cannot connect to trading API at {TRADING_API_URL}: {e}")


def _invoke_trading_lambda(
    method: str,
    path: str,
    trading_user_id: str,
    body: Optional[Dict] = None,
    query_params: Optional[Dict] = None,
) -> Dict:
    """Invoke the trading Lambda directly with a synthetic API GW HTTP v2 event."""
    if not TRADING_LAMBDA_FUNCTION_NAME:
        raise ValueError("TRADING_LAMBDA_FUNCTION_NAME is not configured")

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
            "authorizer": {"claims": {"sub": trading_user_id}},
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


def _invoke_trading_api(
    method: str,
    path: str,
    trading_user_id: str,
    body: Optional[Dict] = None,
    query_params: Optional[Dict] = None,
) -> Dict:
    """Route to either HTTP (local) or Lambda (production) based on configuration."""
    if TRADING_API_URL:
        return _invoke_trading_http(method, path, trading_user_id, body, query_params)
    else:
        return _invoke_trading_lambda(method, path, trading_user_id, body, query_params)


def _send_ses_email(subject: str, body_text: str) -> Dict:
    """Send an email notification via AWS SES."""
    if not SES_SENDER_EMAIL or not NOTIFICATION_EMAIL:
        print("SES not configured — skipping email")
        return {"status": "skipped", "reason": "SES_SENDER_EMAIL or NOTIFICATION_EMAIL not set"}

    try:
        ses_client.send_email(
            Source=f"Shivom's Twin <{SES_SENDER_EMAIL}>",
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


def _execute_tool(tool_name: str, tool_input: Dict, trading_user_id: Optional[str] = None) -> Dict:
    """Route a tool call to the appropriate handler."""
    # Read-only trading tools
    if tool_name == "get_holdings":
        return _invoke_trading_api("GET", "/holdings", trading_user_id=trading_user_id)
    if tool_name == "get_positions":
        return _invoke_trading_api("GET", "/positions", trading_user_id=trading_user_id)
    if tool_name == "get_pnl":
        period = tool_input.get("period", "week")
        return _invoke_trading_api("GET", "/pnl", trading_user_id=trading_user_id, query_params={"period": period})
    if tool_name == "get_funds":
        return _invoke_trading_api("GET", "/funds", trading_user_id=trading_user_id)
    if tool_name == "list_orders":
        return _invoke_trading_api("GET", "/orders", trading_user_id=trading_user_id)
    if tool_name == "get_order":
        order_id = tool_input.get("order_id")
        return _invoke_trading_api("GET", f"/orders/{order_id}", trading_user_id=trading_user_id)
    
    # Write trading tools
    if tool_name == "place_order":
        return _invoke_trading_api("POST", "/orders", trading_user_id=trading_user_id, body=tool_input)
    if tool_name == "modify_order":
        order_id = tool_input.get("order_id")
        return _invoke_trading_api("PUT", f"/orders/{order_id}", trading_user_id=trading_user_id, body=tool_input)
    if tool_name == "cancel_order":
        order_id = tool_input.get("order_id")
        return _invoke_trading_api("DELETE", f"/orders/{order_id}", trading_user_id=trading_user_id)
    
    # Forever (GTC) order tools
    if tool_name == "list_forever_orders":
        return _invoke_trading_api("GET", "/forever/orders", trading_user_id=trading_user_id)
    if tool_name == "place_forever_order":
        return _invoke_trading_api("POST", "/forever/orders", trading_user_id=trading_user_id, body=tool_input)
    if tool_name == "modify_forever_order":
        order_id = tool_input.get("order_id")
        return _invoke_trading_api("PUT", f"/forever/orders/{order_id}", trading_user_id=trading_user_id, body=tool_input)
    if tool_name == "cancel_forever_order":
        order_id = tool_input.get("order_id")
        return _invoke_trading_api("DELETE", f"/forever/orders/{order_id}", trading_user_id=trading_user_id)
    
    # Email tool
    if tool_name == "send_email_notification":
        return _send_ses_email(tool_input["subject"], tool_input["body"])
    
    raise ValueError(f"Unknown tool: {tool_name}")


@app.get("/health")
async def health_check():
    mode = "HTTP (local)" if TRADING_API_URL else "Lambda (production)" if TRADING_LAMBDA_FUNCTION_NAME else "disabled"
    return {
        "status": "healthy", 
        "use_s3": USE_S3,
        "bedrock_model": BEDROCK_MODEL_ID
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, request: Request):
    try:
        # Generate session ID if not provided
        session_id = chat_request.session_id or str(uuid.uuid4())

        # Resolve trading user ID from JWT claims when trading context is requested
        trading_user_id: Optional[str] = None
        if chat_request.context == "trading":
            trading_user_id = _extract_user_id(request)
            if not trading_user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Trading context requires authentication (Cognito JWT or DEV_USER_ID)",
                )

        # Load conversation history
        conversation = load_conversation(session_id)

        # Extract JWT claims from request
        user_claims = _extract_user_claims(request)
        
        # Build context-specific tool config and call Bedrock
        tool_config = _build_tool_config(chat_request.context, trading_user_id)
        assistant_response, quick_options = call_bedrock_with_tools(
            conversation, chat_request.message, tool_config, trading_user_id, chat_request.context, user_claims
        )

        # Update conversation history
        conversation.append(
            {"role": "user", "content": chat_request.message, "timestamp": datetime.now().isoformat()}
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

        return ChatResponse(response=assistant_response, session_id=session_id, options=quick_options)

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