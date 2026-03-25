# Twin API Service — Terraform Documentation

## Overview

The **twin-api** service is an AWS Lambda-based agentic chat API powered by Amazon Bedrock. It provides REST endpoints for conversational AI with tool integration capabilities, including email notifications.

**Key Features:**
- Agentic conversation endpoint with multi-turn dialogue support
- Tool-use integration with Bedrock (email notifications)
- Conversation memory storage in S3 (with local file fallback for development)
- Email notifications via AWS SES for out-of-scope requests
- Optional JWT authentication via Cognito
- Optional WAF-based origin protection (for CloudFront-only access)
- RESTful HTTP API v2 (API Gateway HTTP API)

---

## Quick Architecture

```
┌──────────────────────────────────────┐
│    API Gateway HTTP API              │
│  (POST /chat, GET /health, etc.)     │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│    Lambda Function (Python 3.12)     │
│  - Bedrock agentic loop              │
│  - SES email dispatch                │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ S3 Bucket    │
        │ (Memory)     │
        └──────────────┘

Optional: WAF WebACL (blocks direct API access, allows CloudFront only)
```

---

## Project Structure

```
terraform/services/twin-api/         # Terraform infrastructure config for this service
├── main.tf                           # Core infrastructure (Lambda, API Gateway, S3, IAM)
├── variables.tf                      # Input variables (bedrock_model_id, timeouts, auth, etc.)
├── outputs.tf                        # Exported values (API URL, Lambda name, S3 bucket, etc.)
├── versions.tf                       # Terraform version and provider requirements
└── terraform.tfvars                  # Static configuration (bedrock model, email addresses)

Backend Lambda Source: ./
├── lambda_handler.py       # Mangum wrapper for FastAPI
├── server.py               # FastAPI app with /chat, /health endpoints
├── context.py              # System prompt builder
└── requirements.txt        # Python dependencies (fastapi, boto3, bedrock-runtime)
```

---

## Terraform Variables

All variables are defined in `variables.tf`. Below are the service-specific and important configurable inputs:

### Required Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `project_name` | string | `"twin"` | Prefix for all AWS resource names (e.g., `twin-dev-twin-api`). Validated: lowercase letters, numbers, hyphens only. |
| `environment` | string | — | Deployment environment: `dev`, `test`, or `prod`. Controls state file paths and resource naming. |
| `ses_sender_email` | string | — | **Required.** Verified SES sender email address (e.g., `<yourdomain.com>`). Must be verified in AWS SES in the target region. |

### Optional Variables (with Defaults)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `bedrock_model_id` | string | `amazon.nova-micro-v1:0` | Amazon Bedrock model ID for inference. Examples: `amazon.nova-micro-v1:0`, `amazon.nova-lite-v1:0`, `us.anthropic.claude-opus-4-1-20250805-v1:0`. Must be available in your AWS account. |
| `lambda_timeout` | number | `60` | Lambda function timeout in seconds. Set higher for complex queries (max 900 seconds). |
| `api_throttle_burst_limit` | number | `10` | API Gateway burst throttle limit (requests per burst). |
| `api_throttle_rate_limit` | number | `5` | API Gateway sustained throttle rate (requests per second). |
| `enable_origin_protection` | bool | `false` | If `true`, creates a WAF WebACL that **blocks all direct API Gateway access** and only allows requests from CloudFront with the correct `x-origin-verify` header. **Costs money.** Recommended: `true` for production. |
| `notification_email` | string | `<OWNER_EMAIL>` | Recipient email for owner notifications when tools are executed or out-of-scope requests occur. |

### Cognito Authentication Variables (Optional)

Enable JWT-based authentication on the `/chat` endpoint by setting `enable_cognito_auth = true` and providing:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_cognito_auth` | bool | `false` | If `true`, POST /chat requires a valid Cognito JWT in the `Authorization` header. Other endpoints (GET /, GET /health) remain public. |
| `cognito_user_pool_id` | string | `null` | Cognito User Pool ID (e.g., `us-east-1_XXXXXXXXX`). **Required if `enable_cognito_auth = true`.** |
| `cognito_app_client_id` | string | `null` | Cognito App Client ID. **Required if `enable_cognito_auth = true`.** |
| `cognito_region` | string | `us-east-1` | AWS region where your Cognito User Pool is deployed. |

### Example: Typical Production Configuration

```hcl
# terraform.tfvars (or pass via -var flags)
project_name               = "twin"
environment                = "prod"
bedrock_model_id           = "amazon.nova-micro-v1:0"
lambda_timeout             = 90
api_throttle_burst_limit   = 20
api_throttle_rate_limit    = 10
enable_origin_protection   = true
enable_cognito_auth        = true
notification_email         = "<OWNER_EMAIL>"
cognito_user_pool_id       = "us-east-1_XXXXXXXXX"
cognito_app_client_id      = "YYYYYYYYYYYYYYYYYYYY"
cognito_region             = "us-east-1"
```

---

## Lambda Environment Variables

These are set automatically by Terraform during deployment. Understand them for debugging and local development:

| Variable | Source | Example | Description |
|----------|--------|---------|-------------|
| `CORS_ORIGINS` | Foundation state | `https://example.com,https://app.example.com` | Comma-separated list of trusted origins. Used in API Gateway CORS policy. Set by foundation Terraform state. |
| `S3_BUCKET` | Terraform | `twin-prod-memory-<ACCOUNT_ID>` | S3 bucket for conversation memory (created by this service). |
| `USE_S3` | Hardcoded | `"true"` | Always true in production. Conversation history stored in S3 instead of local files. |
| `BEDROCK_MODEL_ID` | Variable | `amazon.nova-micro-v1:0` | Model ID passed to Bedrock API for inference. Determines cost, latency, and quality. |
| `ORIGIN_VERIFY_SECRET` | Generated | `<32-char random string>` | Secret sent as `x-origin-verify` header by CloudFront to prove origin. Randomly generated and never shared. |
| `SES_SENDER_EMAIL` | Variable | `<domain>` | Verified SES sender email. Used as `From:` in email notifications. |
| `NOTIFICATION_EMAIL` | Variable | `<OWNER_EMAIL>` | Owner's email address. Used as `To:` recipient for notifications. |
| `SES_REGION` | `.env` (local) | `us-east-1` | AWS region for SES. Defaults to `AWS_REGION_NAME` if unset. Only needed locally when your SES identity is in a different region than Bedrock. |

### Local Development Variables

When running locally, also set:

| Variable | Value | Purpose |
|----------|-------|---------|
| `AWS_PROFILE_NAME` | `<your-profile>` | AWS CLI profile name for local Bedrock/SES access. |

---

## API Endpoints

### 1. GET / — Welcome

**Public (always accessible)**

```bash
curl https://<API_GATEWAY_URL>/
```

**Response:**
```json
{
  "status": "healthy",
  "use_s3": true,
  "bedrock_model": "amazon.nova-micro-v1:0"
}
```

---

### 2. GET /health — Health Check

**Public (always accessible)**

```bash
curl https://<API_GATEWAY_URL>/health
```

**Response:**
```json
{
  "status": "healthy",
  "use_s3": true,
  "bedrock_model": "amazon.nova-micro-v1:0"
}
```

---

### 3. POST /chat — Conversational Chat with Tools

**Authentication:** 
- If `enable_cognito_auth = false`: Public (no auth required)
- If `enable_cognito_auth = true`: Requires Cognito JWT in `Authorization: Bearer <TOKEN>` header

**Request:**
```json
{
  "message": "Tell me about yourself",
  "session_id": "<OPTIONAL_UUID>",
  "context": "conversation"
}
```

**Parameters:**
- `message` (required): User's message to the LLM
- `session_id` (optional): Unique session identifier (UUID). If omitted, a new one is generated. Reuse to maintain conversation history.
- `context` (optional, default: `"conversation"`): Currently only `"conversation"` is supported — general chat with email notification tool.

**Response:**
```json
{
  "response": "I'm Shivom's digital twin...",
  "session_id": "<UUID>",
  "options": ["Tell me more", "Contact Shivom"]
}
```

**Response Fields:**
- `response`: Assistant's response text
- `session_id`: Session ID (same as request or newly generated)
- `options` (optional): Quick-option suggestions extracted from LLM output (if present)

**Example Requests:**

```bash
curl -X POST https://<API_GATEWAY_URL>/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about yourself",
    "context": "conversation"
  }'
```

With an existing session:
```bash
curl -X POST https://<API_GATEWAY_URL>/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <COGNITO_JWT_TOKEN>" \
  -d '{
    "message": "What projects have you worked on?",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "context": "conversation"
  }'
```

---

### 4. GET /conversation/{session_id} — Retrieve Conversation History

**Public (always accessible)**

Retrieve the full conversation history for a given session.

```bash
curl https://<API_GATEWAY_URL>/conversation/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "Tell me about yourself",
      "timestamp": "2026-03-24T10:30:00.000Z"
    },
    {
      "role": "assistant",
      "content": "I'm Shivom's digital twin...",
      "timestamp": "2026-03-24T10:30:05.000Z"
    }
  ]
}
```

---

## Tool Integrations

The Lambda function uses Bedrock's tool-use feature to call functions on behalf of the LLM.

### Available Tool

- **send_email_notification**
  - **Use case:** When a visitor asks something outside your knowledge, requests custom actions, or explicitly asks to contact the owner.
  - **Parameters:** `subject` (string), `body` (string)
  - **Returns:** Confirmation that email was sent or failed
  - **Best practice:** Use as a last resort. Try to answer from context first, ask clarifying questions, provide alternatives. Only escalate via email when truly unresolvable.

---

## Authentication & Authorization

### Chat Endpoint

- **Without Cognito** (`enable_cognito_auth = false`): `POST /chat` is public — no token required.
- **With Cognito** (`enable_cognito_auth = true`): Requires a valid Cognito JWT in the `Authorization: Bearer <TOKEN>` header. JWT must include `sub` claim and match the configured `cognito_app_client_id`. Other endpoints (`GET /`, `GET /health`) remain public.

### JWT Claims Used

When Cognito is enabled, the Lambda reads available claims (name, email, etc.) from the JWT to personalise responses and include them in email notifications sent to the owner.

---

## Conversation Memory

### Storage Modes

**Production Mode** (Lambda deployed):
- `USE_S3 = "true"`
- Conversations stored in S3 bucket: `<PROJECT>-<ENV>-memory-<ACCOUNT_ID>`
- Each session ID maps to a JSON file in the bucket
- Persists across Lambda executions and function redeploys
- Requires S3 read/write permissions (granted via IAM policy)

**Local Development Mode** (running locally):
- `USE_S3 = "false"` (comment out or set in `.env`)
- Conversations stored in local `../memory/` directory (relative to backend/)
- Each session ID maps to a `.json` file
- Discarded when local directory is cleaned

### Session ID Behavior

- **If provided in request:** Uses the provided session ID, loads existing conversation if present
- **If omitted:** Generates a new UUID v4, starts a fresh conversation
- **Reusing a session ID:** Loads all previous messages, appends new message, maintains full context for the LLM

### Retention Policy

- No automatic cleanup or TTL on memory files
- S3 Bucket has no lifecycle policies configured (manual cleanup or configure via Terraform if desired)
- Conversation history persists indefinitely unless manually deleted

---

## Origin Protection (WAF)

### Overview

When `enable_origin_protection = true`, a WAF WebACL is created that:

1. **Blocks all direct API Gateway access** — Requests going directly to the API Gateway URL are rejected
2. **Allows only CloudFront requests** — Requests with the `x-origin-verify: <SECRET>` header are allowed
3. **Secret:** A random 32-character string generated at Terraform apply time (stored in Terraform state)

### Setup

1. Set `enable_origin_protection = true` in Terraform variables
2. Deploy (terraform apply)
3. Retrieve the `origin_verify_secret` from Terraform state or outputs:
   ```bash
   terraform output -raw origin_verify_secret
   ```
4. Provide this secret to the deployment script (`deploy-service.sh`) so CloudFront includes it in its origin requests

### Cost Impact

- **AWS WAF WebACL:** ~$5–10/month (per web ACL) + ~$0.60 per million requests
- **Recommended:** Enable for production to prevent direct API access, disable for dev/test to reduce costs

### References

- Terraform resource: `aws_wafv2_web_acl` (api_protection)
- Terraform resource: `aws_wafv2_web_acl_association` (api)

---

## Deployment

### Prerequisites

1. **AWS Credentials:** Configured `terraform` profile with permissions to create Lambda, API Gateway, S3, IAM, Bedrock, SES, CloudWatch
2. **Terraform State Backend:** S3 bucket and DynamoDB table must exist (set up by foundation Terraform)
3. **SES Verification:** Sender email must be verified in AWS SES (in target region)
4. **Bedrock Model Access:** Selected model must be enabled in your AWS account

### Deployment Steps

`scripts/deploy-service.sh` handles the full deployment: it builds the Lambda package, runs `terraform init` with the correct backend config, and applies the Terraform module. Manual steps are only needed for first-time variable setup.

#### Step 1: Configure `terraform.tfvars`

Create or update `terraform/services/twin-api/terraform.tfvars` (only needed once or when variables change):

```hcl
project_name             = "twin"
bedrock_model_id         = "amazon.nova-micro-v1:0"
lambda_timeout           = 60
api_throttle_burst_limit = 10
api_throttle_rate_limit  = 5
enable_origin_protection = false
ses_sender_email         = "<YOUR_DOMAIN>"
notification_email       = "<YOUR_EMAIL>"
```

#### Step 2: Deploy

From the repo root:

```bash
# Basic deploy (no Cognito auth)
scripts/deploy-service.sh twin-api dev

# With Cognito auth enabled (pass as env vars)
ENABLE_COGNITO_AUTH=true \
COGNITO_USER_POOL_ID=<USER_POOL_ID> \
COGNITO_APP_CLIENT_ID=<APP_CLIENT_ID> \
COGNITO_REGION=<REGION> \
scripts/deploy-service.sh twin-api dev

# Deploy to prod
scripts/deploy-service.sh twin-api prod
```

The script prints the API Gateway URL and Lambda function name on success.

---

### Deploying the Frontend with Cognito Configuration

The frontend is deployed separately from the backend services. To ensure the frontend has the correct Cognito configuration, pass environment variables to `deploy-frontend.sh`:

```bash
# Basic deploy (no Cognito, uses defaults from .env.local.example)
scripts/deploy-frontend.sh dev

# With Cognito config (recommended for production)
COGNITO_DOMAIN=<OAUTH_DOMAIN> \
COGNITO_USER_POOL_ID=<USER_POOL_ID> \
COGNITO_APP_CLIENT_ID=<APP_CLIENT_ID> \
COGNITO_REGION=<REGION> \
scripts/deploy-frontend.sh prod
```

**Example with actual values:**

```bash
COGNITO_DOMAIN=us-east-1uhz7yreuq.auth.us-east-1.amazoncognito.com \
COGNITO_USER_POOL_ID=us-east-1_uhz7yREuQ \
COGNITO_APP_CLIENT_ID=2vn45ed6rbe1c9cg58b2vgpt5u \
COGNITO_REGION=us-east-1 \
scripts/deploy-frontend.sh prod
```

These env vars are injected into `frontend/.env.production` at build time, making the Cognito config dynamic across environments.

**Via GitHub Actions (CI/CD):**

Configure these as [GitHub Secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions) (`COGNITO_DOMAIN`, `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID`, `COGNITO_REGION`), and the deployment workflow will automatically pass them to the deploy script.


#### Key Outputs

After deploy, retrieve outputs manually if needed:

```bash
cd terraform/services/twin-api
terraform output -raw api_gateway_url       # Direct API Gateway URL
terraform output -raw public_url            # CloudFront URL (if wired)
terraform output -raw lambda_function_name  # Lambda name for log tailing
terraform output -raw s3_memory_bucket      # S3 bucket for conversation memory
```

---

## Local Development

### Setup

1. **Prerequisites:** Python 3.12+, virtual environment
2. **Backend setup:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Create `.env` file:**
   ```bash
   # backend/.env
   BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
   AWS_PROFILE_NAME=<YOUR_AWS_PROFILE>
   CORS_ORIGINS=http://localhost:3000,http://localhost:3001
   MEMORY_DIR=../memory
   USE_S3=false
   ```

### Running Locally

```bash
cd backend
source .venv/bin/activate
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Expected: `INFO:     Uvicorn running on http://0.0.0.0:8000`

### Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, tell me about yourself"}'

# Retrieve conversation
curl http://localhost:8000/conversation/550e8400-e29b-41d4-a716-446655440000
```

---

## Troubleshooting

### Bedrock Model Not Available

**Error:** `ResourceNotFoundException` or "The requested model is not available"

**Root Cause:** Specified model is not available/enabled in your AWS account

**Solution:**
1. Check your account's available models in AWS Console: Bedrock → Models
2. Update `bedrock_model_id` variable to an available model
3. Re-apply Terraform

**Common models:**
- `amazon.nova-micro-v1:0` — Small, fast, low cost
- `amazon.nova-lite-v1:0` — Medium
- `us.anthropic.claude-opus-4-1-20250805-v1:0` — Large, slow, high cost

### SES Email Not Sending

**Symptom:** Tool `send_email_notification` fails silently or logs "Error: SES not configured"

**Root Cause:** SES sender email not verified, or SES permissions missing

**Solution:**
1. Verify sender email in AWS Console: SES → Verified Identities (in target region)
   - Add domain and verify via DNS records, or
   - Add email and verify via confirmation link
2. Ensure `SES_SENDER_EMAIL` and `NOTIFICATION_EMAIL` variables are set and valid

### Cognito JWT Authentication Failing

**Error:** HTTP 401 Unauthorized on POST /chat with valid-looking JWT

**Root Cause:**
- JWT not in `Authorization: Bearer <TOKEN>` format
- JWT issued by wrong Cognito User Pool
- JWT expired
- `cognito_app_client_id` or `cognito_user_pool_id` mismatch

**Solution:**
1. Verify JWT format: `Authorization: Bearer <TOKEN>` (not `Bearer<TOKEN>`, with space)
2. Decode JWT (online tool or `jq`) and check:
   - `aud` matches `cognito_app_client_id`
   - `iss` matches `https://cognito-idp.<REGION>.amazonaws.com/<USER_POOL_ID>`
   - `exp` is in the future
3. Re-check Terraform variables match your Cognito setup:
   ```bash
   terraform output | grep cognito
   ```
4. For local testing, disable Cognito: `enable_cognito_auth = false`

---

## Testing Checklist

Before deploying to production:

- [ ] Build Lambda package: `uv run deploy.py` (no errors, zip created)
- [ ] Terraform init succeeds with correct backend config
- [ ] Terraform plan shows expected resources (Lambda, API Gateway, S3, IAM)
- [ ] Terraform apply succeeds
- [ ] Retrieve API Gateway URL: `terraform output api_gateway_url`
- [ ] Test `/health` endpoint: HTTP 200, returns JSON
- [ ] Test `/chat`: HTTP 200, receives response
- [ ] If Cognito enabled: Test with valid JWT, receives response; test without JWT, gets HTTP 401
- [ ] Test `send_email_notification` tool, email arrives in inbox
- [ ] Test `/conversation/{session_id}` with valid session, retrieves history
- [ ] Check CloudWatch Logs for Lambda errors: `/aws/lambda/<PROJECT>-<ENV>-twin-api`
- [ ] If origin protection enabled: Direct API access blocked (403), CloudFront access works

---

## Important Notes

### Costs

- **Lambda:** ~$0.20/million requests + compute time (~$16.67/million compute-seconds at 128 MB)
- **API Gateway:** ~$3.50/million requests
- **S3:** ~$0.023/GB/month storage + request charges
- **Bedrock:** Varies by model (~$0.08/1K input tokens, $0.24/1K output tokens for nova-micro)
- **WAF:** ~$5–10/month per Web ACL + ~$0.60/million requests (if enabled)
- **SES:** First 62,000 emails/month free, then $0.10/1000 emails

### Bedrock Model Selection

- **amazon.nova-micro-v1:0** (default): Fastest, cheapest, good for Q&A and tool use
- **amazon.nova-lite-v1:0**: Slightly larger, better for complex reasoning
- **us.anthropic.claude-opus-4-1-20250805-v1:0**: Largest, most capable, slowest, most expensive

Choose based on your needs. Micro is recommended for most use cases.

### Session ID Persistence

Reuse the same `session_id` to maintain multi-turn conversations. The LLM sees the full conversation history (up to 50 previous messages). Session data persists in S3 indefinitely (consider implementing a cleanup/archival strategy).

### Lambda Timeout Considerations

- Default: 60 seconds
- Bedrock API calls + tool invocations can take 10–30 seconds
- Set `lambda_timeout` higher if you see timeouts: Increase to 90 or 120 seconds
- Maximum: 900 seconds (15 minutes)

---

## Related Resources

- **Terraform Service Config:** `../terraform/services/twin-api/` (infrastructure definitions)
- **Foundation Terraform:** `../terraform/foundation/` (CloudFront, custom domain, shared infrastructure)
- **Bedrock Documentation:** https://docs.aws.amazon.com/bedrock/latest/userguide/
- **API Gateway HTTP API:** https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html

---

## Support & Debugging

For issues:

1. **Check CloudWatch Logs:** `aws logs tail /aws/lambda/<PROJECT>-<ENV>-twin-api --follow`
2. **Inspect Lambda Configuration:** `aws lambda get-function-configuration --function-name <NAME>`
3. **Verify Bedrock Access:** Test Bedrock model availability in AWS Console or CLI
5. **Review Terraform State:** `terraform show` or `terraform state list`

---

**Last Updated:** 2026-03-24  
**Service:** twin-api  
**Environment:** Across dev, test, prod deployments
