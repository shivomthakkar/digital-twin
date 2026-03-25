# Terraform Infrastructure Module

A **standalone, reusable infrastructure-as-code module** for serverless APIs and static frontend hosting on AWS. This module is suitable for any codebase (Python, Node.js, etc.) and provides a complete production-ready setup with CloudFront CDN, API Gateway + Lambda, S3 frontend hosting, and optional custom domain support.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Variable Reference](#variable-reference)
- [Output Reference](#output-reference)
- [Deployment Workflows](#deployment-workflows)
- [Adding a New Service](#adding-a-new-service)
- [Architecture Patterns & Quirks](#architecture-patterns--quirks)
- [Advanced Topics](#advanced-topics)
- [Pricing & Free Tier](#pricing--free-tier)
- [Troubleshooting](#troubleshooting)
- [Cleanup & Removal](#cleanup--removal)

---

## Overview

This module creates a **three-layer infrastructure**:

1. **Bootstrap** — AWS account setup (S3 state bucket, DynamoDB locks)
2. **Foundation** — Shared infrastructure (CloudFront distribution, S3 frontend bucket, DynamoDB tables, IAM policies)
3. **Services** — Independent, deployable API microservices

### Key Features

- ✅ **Multi-service** — Deploy unlimited API services independently; all wired automatically to CloudFront
- ✅ **Standalone** — No mandatory Python/Node.js structure; services can be any runtime
- ✅ **State management** — Remote S3 backend with DynamoDB locks for safe concurrent deployments
- ✅ **CDN-ready** — CloudFront distribution with automatic origin protection via custom headers
- ✅ **Optional custom domain** — Route53 + ACM certificates (when enabled)
- ✅ **Cognito integration** — Optional JWT authentication; injectable per deployment
- ✅ **Shared user profiles** — DynamoDB table for cross-service user data access
- ✅ **CORS auto-configured** — Frontend URLs automatically computed and provided to services

### Suitable For

- Serverless API backends (Lambda + API Gateway)
- Static frontend hosting (S3 + CloudFront)
- Multi-tenant SaaS with shared user profiles
- Microservices with incremental service deployments
- Development, staging, and production environments

---

## Prerequisites

### Required Tools

| Tool | Version | Installation |
|------|---------|--------------|
| Terraform | >= 1.0 | https://www.terraform.io/downloads |
| AWS CLI | >= 2.0 | https://aws.amazon.com/cli/ |
| jq | >= 1.6 | `brew install jq` (macOS) / `apt-get install jq` (Ubuntu) |
| bash | >= 4.0 | macOS: system default / Ubuntu: system default |

### AWS Account Setup

**Permissions required:**

- S3 (create buckets, manage versioning, public access blocks)
- Lambda (create functions, upload packages, manage execution roles)
- API Gateway (create HTTP APIs, manage authorizers, throttling)
- CloudFront (create distributions, functions, manage origins)
- IAM (create roles, policies, attach to resources)
- DynamoDB (create tables, manage billing mode)
- CloudWatch (logs, monitoring)
- Route53 + ACM (only if using custom domain)
- Cognito (only if using Cognito auth)

**AWS Profile Configuration:**

Create an AWS profile in `~/.aws/config` with the appropriate region:

```ini
[profile my-profile]
region = {region}  # e.g., ap-south-1, us-east-1, eu-west-1
```

Specify the profile when running scripts: `AWS_PROFILE=my-profile scripts/bootstrap.sh`

---

## Quick Start

This section gets you from zero to a deployed API in ~5 minutes.

### Step 1: Bootstrap AWS Account (One-Time Only)

```bash
cd /path/to/terraform-module
scripts/bootstrap.sh
```

**What happens:**
- Creates S3 bucket: `<project-name>-terraform-state-{ACCOUNT_ID}`
- Creates DynamoDB table: `<project-name>-terraform-locks`
- **Idempotent** — safe to re-run

**Expected output:**
```
✅ Bootstrap complete!
   State bucket   : my-project-terraform-state-{account-id}
   DynamoDB table : my-project-terraform-locks
```

### Step 2: Deploy Foundation Infrastructure

```bash
scripts/setup-infra.sh dev
```

**What happens:**
- Creates CloudFront distribution
- Creates S3 frontend bucket
- Creates DynamoDB user_profiles table
- Creates IAM policies for services
- (Optionally) creates Route53 hosted zone + ACM certificates

**When prompted (or via flags):**
```
Enter environment [{env}]: dev
Use custom domain? [no]: no  # Set to "yes" for custom domain with --domain example.com
```

**Expected output:**
```
✅ Foundation deployed!
   CloudFront URL : https://{cf-domain}.cloudfront.net
   Frontend bucket: {project-name}-frontend-{env}-{account-id}
```

### Step 3: Deploy a Service

```bash
scripts/deploy-service.sh twin-api dev
```

**What happens:**
- Builds Lambda package
- Creates API Gateway + Lambda function
- Wires service into CloudFront distribution
- Updates `service-endpoints.auto.tfvars.json`

**With custom path prefixes:**
```bash
scripts/deploy-service.sh {service-name} dev --paths /{path1} /{path2}
```

**With Cognito auth enabled:**
```bash
AWS_PROFILE=my-profile \
ENABLE_COGNITO_AUTH=true \
COGNITO_USER_POOL_ID={region}_{pool_id} \
COGNITO_APP_CLIENT_ID={app_client_id} \
scripts/deploy-service.sh {service-name} dev
```

**Expected output:**
```
✅ Service '{service-name}' deployed!
   API Gateway URL: https://{api-id}.execute-api.{region}.amazonaws.com/
   Lambda function: {service-name}-{env}

✅ CloudFront updated — public endpoint: https://{cf-domain}.cloudfront.net/{path}
```

### Step 4: Deploy Frontend (Optional)

```bash
# Deploy without Cognito (uses defaults from .env.local.example)
scripts/deploy-frontend.sh dev

# Deploy with Cognito configuration
COGNITO_DOMAIN=<oauth_domain> \
COGNITO_USER_POOL_ID=<pool_id> \
COGNITO_APP_CLIENT_ID=<client_id> \
COGNITO_REGION=<region> \
scripts/deploy-frontend.sh prod
```

**What happens:**
- Reads all deployed service URLs from Terraform state
- Injects Cognito OAuth configuration into `frontend/.env.production` (from env vars)
- Builds Next.js frontend (sets `NEXT_PUBLIC_*` env vars for each service and Cognito)
- Uploads static assets to S3
- Invalidates CloudFront cache

**Cognito Configuration:**

The frontend reads Cognito configuration from environment variables:
- `COGNITO_DOMAIN` → `NEXT_PUBLIC_COGNITO_DOMAIN`
- `COGNITO_USER_POOL_ID` → `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
- `COGNITO_APP_CLIENT_ID` → `NEXT_PUBLIC_COGNITO_CLIENT_ID`
- `COGNITO_REGION` → `NEXT_PUBLIC_COGNITO_REGION`

If not provided, defaults to placeholder values (suitable for local development only).

**Via CI/CD:**

Set these as GitHub Secrets (`COGNITO_DOMAIN`, `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID`, `COGNITO_REGION`), and GitHub Actions will automatically pass them to `deploy-frontend.sh`.

---

## Architecture

### Layer 1: Bootstrap

**Directory:** `terraform/bootstrap/`

**Purpose:** One-time AWS account setup. Creates remote state backend.

**When to run:** Once per AWS account (idempotent).

**Resources created:**
- **S3 bucket** (`{project-name}-terraform-state-{account-id}`)
  - Versioning enabled
  - Server-side encryption (AES256)
  - Public access blocked
  - Used to store all terraform state for foundation + services
  
- **DynamoDB table** (`{project-name}-terraform-locks`)
  - On-demand billing
  - Hash key: `LockID`
  - Used to prevent concurrent terraform applies

**Expected outputs:**
```
state_bucket_name = "my-project-terraform-state-{account-id}"
dynamodb_table_name = "my-project-terraform-locks"
```

**Files:**
- `main.tf` — S3 bucket + DynamoDB table definitions
- `outputs.tf` — Bucket and table names
- `versions.tf` — Provider and Terraform version constraints
- `terraform.tfstate` — Local state (safe to delete after first run)

### Layer 2: Foundation

**Directory:** `terraform/foundation/`

**Purpose:** Shared infrastructure used by all services.

**When to run:** After bootstrap; re-run when adding new services or changing domain config.

**Key resources:**

- **CloudFront Distribution**
  - Distributes frontend (S3 origin) 
  - Routes API requests to service API Gateways (dynamic origins)
  - CloudFront Functions rewrite paths (remove service prefix before forwarding to Lambda)
  - Protected by `x-origin-verify` header (prevents direct API Gateway access)
  
- **S3 Frontend Bucket**
  - Hosts static assets (HTML, JS, CSS)
  - CloudFront serves all requests to `/` (except `/api/*` patterns)
  
- **DynamoDB User Profiles Table**
  - Schema: Partition key = `cognito_user_id` (string)
  - Used by services to store/retrieve per-user data
  - Generated IAM policy grants GetItem, PutItem, UpdateItem
  
- **Route53 + ACM** (optional, when `use_custom_domain=true`)
  - Creates hosted zone for custom domain
  - Issues ACM certificate for CloudFront
  - Must point NS records at your domain registrar
  
- **IAM Policies**
  - `user_profiles_access_policy` — Allows services to read/write user profiles table

**Backend configuration:**
```
Bucket: {project-name}-terraform-state-{account-id}
Key: foundation/{environment}/terraform.tfstate
DynamoDB table: {project-name}-terraform-locks
```

**Files:**
- `main.tf` — CloudFront, S3, DynamoDB, Route53, ACM, IAM definitions
- `variables.tf` — Input variables (see [Variable Reference](#variable-reference))
- `outputs.tf` — CloudFront URL, CORS origins, table names, wired services map
- `versions.tf` — Provider constraints and backend configuration
- `terraform.tfvars` — Default values (customize as needed)
- `service-endpoints.auto.tfvars.json` — Auto-generated by `deploy-service.sh` (do not edit manually)
- `prod.tfvars` (optional) — Production-specific overrides

### Layer 3: Services

**Directory:** `terraform/services/`

**Purpose:** Independent, deployable API microservices.

**When to run:** Each service deployed independently.

**Template structure:**

```
terraform/services/
├── _template/              # Template for new services
│   ├── main.tf.tmpl
│   ├── variables.tf.tmpl
│   ├── outputs.tf.tmpl
│   ├── versions.tf.tmpl
│   └── README.md
├── twin-api/               # Example: AI/LLM endpoint
├── trading-api/            # Example: Trading operations
└── stock-scraper-api/      # Example: Stock data scraping
```

**Service contract** — Every service MUST:

1. **Export outputs** required by foundation:
   - `api_gateway_url` — REST API Gateway invoke URL
   - `service_name` — Service identifier (folder name)
   - `public_url` — Public URL via CloudFront (auto-computed during wiring)
   - `origin_verify_secret` — Random secret header for CloudFront origin verification
   - `lambda_function_name` — Lambda function name

2. **Read from foundation state** via `terraform_remote_state` data source:
   - `cors_origins` — CloudFront URL + localhost:3000 (for CORS headers)
   - `user_profiles_table_name` — DynamoDB table for user profiles

3. **Set Lambda environment variables:**
   - `CORS_ORIGINS` — From foundation output
   - `ORIGIN_VERIFY_SECRET` — From service output
   - `USER_PROFILES_TABLE` — From foundation output (if service needs it)

**Backend configuration (all services):**
```
Bucket: {project-name}-terraform-state-{account-id}
Key: services/{service-name}/{environment}/terraform.tfstate
DynamoDB table: {project-name}-terraform-locks
```

**Files per service:**
- `main.tf` — Lambda function, API Gateway, IAM roles, service-specific resources
- `variables.tf` — Input variables (contract section must match other services exactly)
- `outputs.tf` — Required contract outputs + service-specific outputs
- `versions.tf` — Provider constraints and backend configuration template
- `terraform.tfvars` — Default values (customize as needed)
- `prod.tfvars` (optional) — Production-specific overrides

**Implemented services:**

1. **twin-api** (`/api`)
   - Purpose: AI/LLM chat endpoint
   - Key resources: Lambda, API Gateway, S3 memory bucket (for conversation context)
   - Models: Amazon Bedrock integration
   - Special vars: `bedrock_model_id`, `lambda_timeout`

2. **trading-api** (`/trading`)
   - Purpose: Broker trading operations (Dhan integration)
   - Key resources: Lambda, API Gateway, Cognito JWT authorizer
   - Routes: `/health`, `/auth/generate-token`, `/auth/renew-token`
   - Special vars: `enable_cognito_auth` (recommended: true)

3. **stock-scraper-api** (`/real-time`)
   - Purpose: Stock data scraping and financial document storage
   - Key resources: Lambda, API Gateway, 3 DynamoDB tables (StockFinancials, StockDocuments, StockSections)
   - Schema: Partition key = symbol, Sort key = scraped_at timestamp
   - Special vars: `enable_cognito_auth`

### How Services Are Wired to CloudFront

```
1. Service deployed → Outputs api_gateway_url + origin_verify_secret
2. deploy-service.sh merges service into service-endpoints.auto.tfvars.json
3. Foundation re-applies with new service-endpoints.auto.tfvars.json
4. CloudFront creates new origin for service's API Gateway
5. CloudFront function rewrites paths (strips /api prefix, forwards to Lambda)
6. Service state refreshed → public_url output updated
```

**Example flow:**
```
User requests: https://{cf-domain}.cloudfront.net/{path}/endpoint
              ↓
CloudFront sees /{path}/* matches service {service-name}
              ↓
CloudFront function rewrites to /endpoint, adds x-origin-verify header
              ↓
Request forwarded to API Gateway origin (https://{api-id}.execute-api.{region}.amazonaws.com/)
              ↓
Lambda receives /endpoint (prefix stripped), processes request
              ↓
Response returned through CloudFront
```

---

## Variable Reference

### Foundation Variables

**File:** `terraform/foundation/terraform.tfvars`

| Variable | Type | Required | Default | Description | Validation |
|----------|------|----------|---------|-------------|-----------|
| `project_name` | string | Yes | — | Name prefix for all resources | Lowercase letters, numbers, hyphens only |
| `environment` | string | Yes | — | Environment name | Must be: `dev`, `test`, or `prod` |
| `use_custom_domain` | bool | No | `false` | Enable custom domain + Route53 | Boolean |
| `root_domain` | string | No* | `""` | Apex domain (e.g., `mydomain.com`) | Required if `use_custom_domain=true` |
| `api_services` | map | No | `{}` | Auto-populated service endpoints | Managed by `deploy-service.sh` — **do not edit manually** |

**auto.tfvars.json lookup (auto-generated):**
```json
{
  "api_services": {
    "service-1": {
      "gateway_url": "https://{api-id-1}.execute-api.{region}.amazonaws.com/",
      "verify_secret": "<random-secret>",
      "path_prefixes": ["/path1"]
    },
    "service-2": {
      "gateway_url": "https://{api-id-2}.execute-api.{region}.amazonaws.com/",
      "verify_secret": "<random-secret>",
      "path_prefixes": ["/path2"]
    }
  }
}
```

**Example terraform.tfvars:**
```hcl
project_name       = "my-project"
environment        = "dev"
use_custom_domain  = false
root_domain        = ""
```

**Example with custom domain:**
```hcl
project_name       = "my-project"
environment        = "prod"
use_custom_domain  = true
root_domain        = "example.com"
```

### Service Contract Variables (All Services)

**File:** `terraform/services/{SERVICE_NAME}/variables.tf`

These variables MUST be present in every service (copy from the contract section in `services/_template/variables.tf.tmpl`).

#### Required (No Default)

| Variable | Type | Description | Validation |
|----------|------|-------------|-----------|
| `project_name` | string | Name prefix for all resources | Lowercase letters, numbers, hyphens only |
| `environment` | string | Environment name | Must be: `dev`, `test`, or `prod` |

#### Optional (Cognito Auth)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_cognito_auth` | bool | `false` | Attach Cognito JWT authorizer to API |
| `cognito_user_pool_id` | string | `null` | Cognito User Pool ID (e.g., `us-east-1_XXXXXXXXX`). **Required if `enable_cognito_auth=true`** |
| `cognito_app_client_id` | string | `null` | Cognito App Client ID. **Required if `enable_cognito_auth=true`** |
| `cognito_region` | string | `"us-east-1"` | AWS region where Cognito User Pool exists |

#### Optional (Service-Specific, Vary by Service)

Examples from implemented services:

**twin-api:**
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `bedrock_model_id` | string | `"amazon.nova-micro-v1:0"` | Amazon Bedrock model for inference |
| `lambda_timeout` | number | `60` | Lambda timeout in seconds |
| `api_throttle_burst_limit` | number | `10` | API Gateway burst limit |
| `api_throttle_rate_limit` | number | `5` | API Gateway rate limit (requests/sec) |
| `enable_origin_protection` | bool | `false` | Enable WAF WebACL to block direct API Gateway access (costs money) |

**trading-api:**
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `lambda_timeout` | number | `30` | Lambda timeout in seconds |
| `api_throttle_burst_limit` | number | `10` | API Gateway burst limit |
| `api_throttle_rate_limit` | number | `5` | API Gateway rate limit (requests/sec) |
| `enable_cognito_auth` | bool | `false` | Enforce Cognito auth (recommended: `true`) |

**stock-scraper-api:**
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `lambda_timeout` | number | `300` | Lambda timeout in seconds (extended for scraping) |
| `api_throttle_burst_limit` | number | `5` | API Gateway burst limit |
| `api_throttle_rate_limit` | number | `2` | API Gateway rate limit (requests/sec) |
| `enable_cognito_auth` | bool | `false` | Enforce Cognito auth |

### Environment Variables (deploy-service.sh)

**Usage:** Export or inline before running `deploy-service.sh`

```bash
AWS_PROFILE=my-profile \
ENABLE_COGNITO_AUTH=true \
COGNITO_USER_POOL_ID={region}_{pool_id} \
COGNITO_APP_CLIENT_ID={app_client_id} \
COGNITO_REGION={region} \
scripts/deploy-service.sh {service-name} {environment}
```

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AWS_PROFILE` | string | `"terraform"` | AWS credentials profile for CLI/Terraform |
| `ENABLE_COGNITO_AUTH` | string | — | Set to `"true"` to enable Cognito; requires `COGNITO_USER_POOL_ID` + `COGNITO_APP_CLIENT_ID` |
| `COGNITO_USER_POOL_ID` | string | — | Cognito User Pool ID (required if `ENABLE_COGNITO_AUTH=true`) |
| `COGNITO_APP_CLIENT_ID` | string | — | Cognito App Client ID (required if `ENABLE_COGNITO_AUTH=true`) |
| `COGNITO_REGION` | string | `"us-east-1"` | AWS region for Cognito User Pool |

### Environment Variables (deploy-frontend.sh)

**Usage:** Export or inline before running `deploy-frontend.sh`

```bash
COGNITO_DOMAIN={oauth_domain} \
COGNITO_USER_POOL_ID={user_pool_id} \
COGNITO_APP_CLIENT_ID={app_client_id} \
COGNITO_REGION={region} \
scripts/deploy-frontend.sh prod
```

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `COGNITO_DOMAIN` | string | `"us-east-1uhz7yreuq.auth.us-east-1.amazoncognito.com"` | Cognito OAuth domain (format: `{region}{pool_suffix}.auth.{region}.amazoncognito.com`) |
| `COGNITO_USER_POOL_ID` | string | `"us-east-1_uhz7yREuQ"` | Cognito User Pool ID (required unless using defaults) |
| `COGNITO_APP_CLIENT_ID` | string | `"2vn45ed6rbe1c9cg58b2vgpt5u"` | Cognito App Client ID (required unless using defaults) |
| `COGNITO_REGION` | string | `"us-east-1"` | AWS region where Cognito User Pool is located |

**Notes:**
- These values are injected into `frontend/.env.production` at build time (visible in compiled Next.js output)
- If not provided, defaults to placeholder values (for local dev; not recommended for production)
- In CI/CD, configure as GitHub Secrets and the deployment workflow will pass them automatically

---

## Output Reference

### Foundation Outputs

**Command to view:**
```bash
terraform -chdir=terraform/foundation output
```

| Output | Type | Description |
|--------|------|-------------|
| `cloudfront_url` | string | HTTPS URL of CloudFront distribution (e.g., `https://{cf-domain}.cloudfront.net`) |
| `cloudfront_distribution_id` | string | CloudFront distribution ID; used for cache invalidations |
| `use_custom_domain` | bool | Whether custom domain is attached |
| `custom_domain_url` | string | Custom domain URL (e.g., `https://mydomain.com`); empty string if not enabled |
| `root_domain` | string | Root domain name; empty string if custom domain not enabled |
| `route53_name_servers` | list(string) | NS records to configure at domain registrar (only if `use_custom_domain=true`). Example: `["ns-{id1}.awsdns-{id2}.com", "ns-{id3}.awsdns-{id4}.com", ...]` |
| `s3_frontend_bucket` | string | S3 bucket name for frontend static assets; deploy-frontend.sh writes here |
| `cors_origins` | string | Comma-separated list of allowed CORS origins. Auto-computed from CloudFront URL or custom domain, always includes `http://localhost:3000`. Example: `https://{cf-domain}.cloudfront.net,http://localhost:3000` |
| `user_profiles_table_name` | string | DynamoDB table name for user profiles; set as `USER_PROFILES_TABLE` env var in Lambda functions |
| `user_profiles_table_arn` | string | ARN of user profiles DynamoDB table; used in IAM policy ARNs |
| `user_profiles_access_policy_arn` | string | ARN of IAM policy granting GetItem/PutItem/UpdateItem on user profiles table; attach to service Lambda roles |
| `wired_services` | map(object) | Map of service name → `{gateway_url, path_prefixes}`; shows currently active services (secrets not exposed) |

**Example output (multiple services):**
```
cloudfront_url = "https://{cf-domain}.cloudfront.net"
cloudfront_distribution_id = "{cf-id}"
s3_frontend_bucket = "my-project-frontend-dev-{account-id}"
cors_origins = "https://{cf-domain}.cloudfront.net,http://localhost:3000"
user_profiles_table_name = "my-project-user-profiles-dev"
user_profiles_table_arn = "arn:aws:dynamodb:{region}:{account-id}:table/my-project-user-profiles-dev"
user_profiles_access_policy_arn = "arn:aws:iam::{account-id}:policy/my-project-user-profiles-access-dev"
wired_services = {
  "service-1" = {
    "gateway_url" = "https://{api-id-1}.execute-api.{region}.amazonaws.com/"
    "path_prefixes" = ["/path1"]
  }
  "service-2" = {
    "gateway_url" = "https://{api-id-2}.execute-api.{region}.amazonaws.com/"
    "path_prefixes" = ["/path2"]
  }
}
```

### Service Contract Outputs

**Command to view:**
```bash
terraform -chdir=terraform/services/{SERVICE} output
```

| Output | Type | Description | Example |
|--------|------|-------------|---------|
| `api_gateway_url` | string | HTTP API Gateway invoke URL; used to wire CloudFront origins | `https://{api-id}.execute-api.{region}.amazonaws.com/` |
| `service_name` | string | Service identifier (must match folder name in `terraform/services/`). Used by deploy-service.sh for state key | `twin-api` |
| `public_url` | string | Public-facing HTTPS URL via CloudFront. Auto-computed during service wiring (first path prefix). Example: `https://{cf-domain}.cloudfront.net/{path}` | `https://{cf-domain}.cloudfront.net/{path}` |
| `origin_verify_secret` | string | Random secret header value. CloudFront includes `x-origin-verify: {secret}` when forwarding to API Gateway. Prevents direct access. | `abcd1234secretkey` |
| `lambda_function_name` | string | AWS Lambda function name; used for local testing, logs, metrics | `twin-api-dev` |

---

## Deployment Workflows

### Workflow 1: First-Time Setup (Per AWS Account & Environment)

**Time:** ~10 minutes (first time only)

```bash
# Step 1: Bootstrap account (one-time, idempotent)
AWS_PROFILE=my-profile scripts/bootstrap.sh

# Step 2: Deploy foundation
AWS_PROFILE=my-profile scripts/setup-infra.sh dev

# Step 3: Deploy first service
AWS_PROFILE=my-profile scripts/deploy-service.sh service-1 dev --paths /path1

# Step 4: Deploy additional services
AWS_PROFILE=my-profile scripts/deploy-service.sh service-2 dev --paths /path2
AWS_PROFILE=my-profile scripts/deploy-service.sh service-3 dev --paths /path3

# Step 5: Deploy frontend (optional)
AWS_PROFILE=my-profile scripts/deploy-frontend.sh dev
```

### Workflow 2: Adding a New Service to Existing Infrastructure

**Time:** ~2 minutes per service

```bash
# Create service (see "Adding a New Service" section)
# ...

# Deploy it
AWS_PROFILE=my-profile scripts/deploy-service.sh {new-service-name} dev --paths /{path}
```

**What happens automatically:**
1. Lambda package built
2. Service terraform applied
3. CloudFront origins updated (merge into service-endpoints.auto.tfvars.json)
4. Foundation re-applied (new service origin added)
5. Service state refreshed (public_url output computed)

### Workflow 3: Updating Foundation Configuration

**Example:** Enable custom domain

```bash
# Edit foundation variables
vim terraform/foundation/terraform.tfvars
# Change: use_custom_domain = false → true
# Change: root_domain = "" → "example.com"

# Re-apply foundation
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation apply
```

**Note:** If services already wired, foundation re-apply preserves them (incremental update).

### Workflow 4: Redeploying a Service (Code Changes)

**Time:** ~2 minutes

```bash
# Service code changed in your backend repo
# Rebuild and redeploy:

AWS_PROFILE=my-profile scripts/deploy-service.sh {service-name} {environment}
```

**What happens:**
1. Backend build system called (e.g., Python `deploy.py`, Node.js esbuild)
2. Lambda package rebuilt and uploaded
3. Service terraform re-applied (function code updated)
4. CloudFront wiring refreshed
5. State refreshed

### Workflow 5: Cognito Integration (Optional)

**Prerequisites:**
- Cognito User Pool exists (e.g., from Amplify)
- App Client created with: Client ID, User Pool ID

```bash
# Deploy service with Cognito auth enabled
AWS_PROFILE=my-profile \
ENABLE_COGNITO_AUTH=true \
COGNITO_USER_POOL_ID={region}_{pool_id} \
COGNITO_APP_CLIENT_ID={app_client_id} \
COGNITO_REGION={region} \
scripts/deploy-service.sh {service-name} dev

# API Gateway now has JWT authorizer
# Requests to protected routes must include: Authorization: Bearer {id_token}
```

### Workflow 6: Custom Domain Setup

**Prerequisites:**
- Domain registered (any registrar)
- Ability to update DNS NS records

```bash
# Step 1: Enable custom domain in foundation
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation apply \
  -var="use_custom_domain=true" \
  -var="root_domain=example.com"

# Step 2: Get nameservers from output
terraform -chdir=terraform/foundation output route53_name_servers
# Output: ["ns-123.awsdns-45.com", "ns-678.awsdns-90.com", ...]

# Step 3: At your domain registrar, update NS records to point to AWS nameservers

# Step 4: Wait ~5-10 minutes for DNS propagation
# Verify: nslookup mydomain.com

# Step 5: CloudFront now uses custom domain
terraform -chdir=terraform/foundation output custom_domain_url
# Output: https://mydomain.com
```

---

## Adding a New Service

This section walks through creating a new, independently deployable API service from scratch.

### Prerequisites

- Service Lambda build script (e.g., `my-service/deploy.py`)
- Understanding of [Service Contract](#layer-3-services) requirements

### Step 1: Copy the Template

```bash
cp -r terraform/services/_template terraform/services/{service-name}

# Rename .tmpl files
for f in terraform/services/{service-name}/*.tmpl; do mv "$f" "${f%.tmpl}"; done
```

**Result:**
```
terraform/services/{service-name}/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
√ README.md
```

### Step 2: Update main.tf

Search for `# REPLACE:` comments and customize:

```hcl
# Change these:
locals {
  service_name = "{service-name}"  # ← Must match folder name
  handler      = "{handler.function}"  # ← Handler function
  runtime      = "{python3.12|nodejs20.x|...}"  # ← Lambda runtime
  timeout      = var.lambda_timeout
}

# Update routes (API Gateway)
resource "aws_api_gateway_resource" "root" {
  # Change path_part to match your API structure
  path_part = "{endpoint-name}"
}

# Update IAM policies if service needs S3, DynamoDB, Bedrock, etc.
# Example: S3 bucket for service
resource "aws_s3_bucket" "memory" {
  bucket = "${local.service_name}-data-${var.environment}"
}
```

### Step 3: Update variables.tf

Keep the **contract section** exactly as-is (copy from template). Add service-specific variables below:

```hcl
# CONTRACT VARIABLES — Copy from _template, do not modify
variable "project_name" { ... }
variable "environment" { ... }
variable "enable_cognito_auth" { ... }
variable "cognito_user_pool_id" { ... }
variable "cognito_app_client_id" { ... }
variable "cognito_region" { ... }

# MY-SERVICE-SPECIFIC VARIABLES
variable "my_custom_timeout" {
  description = "Custom timeout for my service"
  type        = number
  default     = 30
}

variable "memory_bucket_retention_days" {
  description = "Retention days for conversation memory"
  type        = number
  default     = 90
}
```

### Step 4: Update outputs.tf

Keep the **contract outputs** exactly as-is. Add service-specific outputs:

```hcl
# CONTRACT OUTPUTS — Copy from _template, do not modify
output "api_gateway_url" { ... }
output "service_name" { ... }
output "public_url" { ... }
output "origin_verify_secret" { ... }
output "lambda_function_name" { ... }

# MY-SERVICE-SPECIFIC OUTPUTS
output "memory_bucket_name" {
  description = "S3 bucket for storing conversation memory"
  value       = aws_s3_bucket.memory.id
}

output "memory_bucket_arn" {
  description = "ARN of memory bucket"
  value       = aws_s3_bucket.memory.arn
}
```

### Step 5: Create terraform.tfvars

```hcl
project_name           = "my-project"
lambda_timeout         = 30
# Add any other service-specific defaults
```

### Step 6: Update versions.tf

**No changes needed** — the key is auto-injected by `deploy-service.sh`.

### Step 7: Add Lambda Build Step to scripts/deploy-service.sh

Open `scripts/deploy-service.sh` and add an `elif` block in the Lambda build section:

```bash
elif [[ "$SERVICE" == "{service-name}" ]]; then
  (cd "$ROOT/{service-path}" && {build-command})
```

**Examples:**

**Python:**
```bash
elif [[ "$SERVICE" == "my-service" ]]; then
  (cd "$ROOT/my-service" && python build.py)  # or whatever build script you have
```

**Node.js:**
```bash
elif [[ "$SERVICE" == "my-service" ]]; then
  (cd "$ROOT/my-service" && npm install && npm run build && npm run package)
```

**Go:**
```bash
elif [[ "$SERVICE" == "my-service" ]]; then
  (cd "$ROOT/my-service" && go build -o bootstrap && zip function.zip bootstrap)
```

### Step 8: Deploy the Service

```bash
# Basic deployment
AWS_PROFILE=my-profile scripts/deploy-service.sh {service-name} dev --paths /{path}

# With Cognito auth
AWS_PROFILE=my-profile \
ENABLE_COGNITO_AUTH=true \
COGNITO_USER_POOL_ID={region}_{pool_id} \
COGNITO_APP_CLIENT_ID={app_client_id} \
scripts/deploy-service.sh {service-name} dev --paths /{path}

# With production overrides
AWS_PROFILE=my-profile scripts/deploy-service.sh {service-name} prod --paths /{path}
```

### Step 9: Verify Service is Wired to CloudFront

```bash
# Check service outputs
AWS_PROFILE=my-profile terraform -chdir=terraform/services/{service-name} output

# Check foundation wired_services list
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation output wired_services

# Make a test request
curl https://{cloudfront-domain}/{path}/health
```

### Step 10 (Optional): Register Service with Frontend

If using Next.js frontend with `scripts/deploy-frontend.sh`, it auto-discovers services:

```bash
# deploy-frontend.sh scans terraform/services/ directory
# Reads api_gateway_url + service_name from each service's state
# Sets NEXT_PUBLIC_{SERVICE_NAME_UPPER}_API_URL env var
# Example: my-service → NEXT_PUBLIC_MY_SERVICE_API_URL

AWS_PROFILE=my-profile scripts/deploy-frontend.sh dev
```

---

## Architecture Patterns & Quirks

### Pattern 1: CloudFront Origin Verification

**Problem:** How to prevent direct access to API Gateway (bypass CloudFront)?

**Solution:** Custom header verification

```
CloudFront → Adds x-origin-verify: {secret-hash} → API Gateway
Direct access → No header → API Gateway blocks (403)
```

**Implementation:**
- Each service outputs `origin_verify_secret` (randomly generated)
- CloudFront function adds header before forwarding to service
- Lambda receives secret in request headers, validates it
- Secret stored securely in Terraform outputs (sensitive=true)
- Secret never exposed in public `wired_services` map

### Pattern 2: Service-Endpoints Auto-Discovery

**Problem:** How to add N services without hardcoding each one in foundation?

**Solution:** JSON tfvars file + merge strategy

```
deploy-service.sh launches service
      ↓
Service outputs api_gateway_url + origin_verify_secret
      ↓
deploy-service.sh reads service-endpoints.auto.tfvars.json
      ↓
Merges new service into JSON (preserves others)
      ↓
Foundation re-applies with updated api_services variable
      ↓
CloudFront origins updated automatically
```

**File:** `terraform/foundation/service-endpoints.auto.tfvars.json`

```json
{
  "api_services": {
    "service-1": {
      "gateway_url": "https://api1.execute-api.{region}.amazonaws.com/",
      "verify_secret": "<random-hash>",
      "path_prefixes": ["/path1"]
    },
    "service-2": {
      "gateway_url": "https://api2.execute-api.{region}.amazonaws.com/",
      "verify_secret": "<random-hash>",
      "path_prefixes": ["/path2", "/path2-v2"]
    }
  }
}
```

When you run `deploy-service.sh my-new-service dev`, the script:
1. Builds service terraform
2. Captures service outputs (api_gateway_url, origin_verify_secret)
3. Uses `jq` to merge into auto.tfvars.json
4. Re-applies foundation

**Advantage:** Services are completely independent; adding a new service requires no changes to foundation code.

### Pattern 3: State Isolation (Per Service)

**Problem:** How to prevent state conflicts when deploying multiple services concurrently?

**Solution:** Separate state files + DynamoDB locks

```
bootstrap/   → Local state (one-time only)
foundation/  → s3://{project-terraform-state-bucket}/foundation/{env}/terraform.tfstate
services/    → s3://{project-terraform-state-bucket}/services/{service_name}/{env}/terraform.tfstate
```

**DynamoDB locks table:** Prevents concurrent applies to same service

**Benefit:** Services can be deployed in parallel:
```bash
# In parallel:
AWS_PROFILE=my-profile scripts/deploy-service.sh service-1 dev &
AWS_PROFILE=my-profile scripts/deploy-service.sh service-2 dev &
AWS_PROFILE=my-profile scripts/deploy-service.sh service-3 dev &
wait
```

### Pattern 4: CORS Origin Auto-Computation

**Problem:** How to tell Lambda which frontend URLs are allowed (CORS)?

**Solution:** Foundation output computes and provides to services

**Logic:**
```hcl
# In foundation/outputs.tf
cors_origins = var.use_custom_domain && var.root_domain != "" ? 
  "https://${var.root_domain},https://www.${var.root_domain},http://localhost:3000" :
  "https://${aws_cloudfront_distribution.main.domain_name},http://localhost:3000"
```

**Flow:**
1. Foundation computes `cors_origins` output
2. Services read via `terraform_remote_state` data source
3. Services set `CORS_ORIGINS` env var on Lambda
4. Lambda reads env var, sets response headers: `Access-Control-Allow-Origin: {cors_origins}`

**Benefit:** Frontend URL is source of truth; no manual configuration needed

### Pattern 5: CloudFront Path Rewriting

**Problem:** How to route `/api/*` requests to API Gateway while serving `/` from S3?

**Solution:** CloudFront Functions + dynamic origins

```
User: GET /api/chat
      ↓
CloudFront checks path patterns (configured in main.tf)
      ↓
Matches /{path}/* → {service-name} origin
      ↓
CloudFront function rewrites path: /api/chat → /chat
      ↓
Request: GET https://api123.execute-api.../chat
      ↓
Lambda handler receives path=/chat (prefix stripped)
      ↓
Response returned to user as /api/chat
```

**Configuration:** Service specifies `path_prefixes` during deploy:
```bash
scripts/deploy-service.sh trading-api dev --paths /trading /v2
```

This tells CloudFront: `/trading/*` and `/v2/*` go to trading-api service.

### Pattern 6: Template + REPLACE Markers

**Problem:** How to standardize service structure while allowing customization?

**Solution:** Template files with REPLACE: comments

```
_template/
├── main.tf.tmpl      ← Search for "# REPLACE:" comments
├── variables.tf.tmpl ← Keep contract section verbatim
├── outputs.tf.tmpl   ← Keep contract outputs verbatim
└── versions.tf.tmpl  ← No changes needed
```

**Benefits:**
- New services follow same structure
- Contract requirements clear
- Updates to contract propagate easily

---

## Advanced Topics

### Multi-Region Deployments

To deploy to a different region (e.g., `us-west-2` instead of default):

**Step 1: Update foundation/versions.tf**

```hcl
provider "aws" {
  profile = var.aws_profile
  region  = "{region}"  # ← Change to your desired region (e.g., us-west-2, eu-west-1)
}

provider "aws" {
  profile = var.aws_profile
  alias   = "us_east_1"
  region  = "us-east-1"  # ← Keep for ACM (required by CloudFront)
}
```

**Step 2: Update service versions.tf files**

Same change as foundation.

**Step 3: Bootstrap & Deploy**

```bash
AWS_PROFILE=my-profile scripts/bootstrap.sh
AWS_PROFILE=my-profile scripts/setup-infra.sh dev
AWS_PROFILE=my-profile scripts/deploy-service.sh {service-name} dev
```

### Custom Lambda Runtimes

Services don't require specific runtimes. Update `main.tf` in your service:

**Python 3.12:**
```hcl
runtime = "python3.12"
handler = "index.handler"
```

**Node.js 20:**
```hcl
runtime = "nodejs20.x"
handler = "index.handler"
```

**Go 1.x:**
```hcl
runtime = "go1.x"
handler = "bootstrap"  # ← Go requires bootstrap handler
```

**Custom Docker image:**
```hcl
image_uri = aws_ecr_image.function.image_uri
# Remove: runtime, handler, filename
```

### Drift Detection

Check for manual changes outside terraform:

```bash
# Foundation
terraform -chdir=terraform/foundation plan

# Services
terraform -chdir=terraform/services/{SERVICE} plan
```

If drift detected, either:
- Apply changes back to code + re-apply terraform
- Run terraform apply to revert manual changes

### Lambda Environment Variables

Services must set these on Lambda:

```python
# In Lambda handler
import os

cors_origins = os.environ.get("CORS_ORIGINS")
user_table = os.environ.get("USER_PROFILES_TABLE")
origin_secret = os.environ.get("ORIGIN_VERIFY_SECRET")
```

Foundation provides `CORS_ORIGINS` and `ORIGIN_VERIFY_SECRET` automatically via `terraform_remote_state`.

### WAF Origin Protection

Enable Web Application Firewall to block non-CloudFront access:

```bash
scripts/deploy-service.sh twin-api dev -var="enable_origin_protection=true"
```

**Cost:** ~$5/month per WAF WebACL

**Benefit:** Prevents direct API Gateway manipulation

### Cognito Integration

Cognito authorizer adds JWT validation to API Gateway. Protected routes require:

```bash
curl -H "Authorization: Bearer {id_token}" \
  https://{cf-domain}.cloudfront.net/{path}/protected
```

**Setup:**
1. Create Cognito User Pool (or use existing)
2. Create App Client (note: User Pool ID, App Client ID)
3. Deploy service with env vars:
   ```bash
   ENABLE_COGNITO_AUTH=true \
   COGNITO_USER_POOL_ID={region}_{pool_id} \
   COGNITO_APP_CLIENT_ID={app_client_id} \
   scripts/deploy-service.sh {service-name} dev
   ```

### Custom Domain DNS Configuration

When using custom domain:

```bash
# Get nameservers
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation output route53_name_servers

# Example output:
["ns-{id1}.awsdns-{id2}.com", "ns-{id3}.awsdns-{id4}.com", "ns-{id5}.awsdns-{id6}.com", "ns-{id7}.awsdns-{id8}.com"]

# At your domain registrar (GoDaddy, Namecheap, etc.):
# 1. Go to DNS settings
# 2. Replace nameservers with those above
# 3. Wait 5-10 minutes for propagation
# 4. Verify: nslookup {root-domain}
```

---

## Pricing & Free Tier

This section breaks down which AWS services are **free or included in free tier** vs. those that **will incur charges**.

### Free by Default

| Service | Free Tier Benefit | Conditions | Notes |
|---------|------------------|------------|-------|
| **Lambda** | 1M requests/month + 400K GB-seconds | Per month (free tier limit) | After free tier: $0.20 per 1M requests |
| **API Gateway (HTTP)** | 750K API calls/month | Per month (free tier limit) | After free tier: $0.35 per 1M API calls |
| **DynamoDB (On-Demand)** | 25 GB storage + 25 capacity units | Per month (free tier limit) | Pay-per-request after free tier: $1.25/GB/month storage |
| **CloudWatch Logs** | 5 GB ingestion/month | Per month (free tier limit) | After free tier: $0.50 per GB ingested |
| **IAM** | Unlimited | Always free | No charges ever |
| **ACM Certificates** | Free when used with CloudFront | CloudFront + qualifying services | $0.75/month if used standalone (not applicable here) |
| **S3 (First 12 Months)** | 5 GB standard storage | AWS account new customer only | After free tier: $0.023/GB/month |

### Will Incur Charges

| Service | Charge Model | Estimated Cost (Low Usage) | Notes |
|---------|--------------|---------------------------|-------|
| **CloudFront (Data Transfer)** | $0.085/GB out (varies by region) | $5-20/month (for low traffic) | First 10 TB/month free for new accounts (free tier only) |
| **CloudFront (Requests)** | $0.01 per 10K HTTP/S requests | <$1/month (low traffic) | 10M requests/month free for new accounts (free tier only) |
| **Route53 (Custom Domain)** | $0.50/hosted zone/month + $0.40 per 1M queries | $0.50-2.00/month | Only if using custom domain; not needed for CloudFront domain |
| **S3 Storage (Beyond Free)** | $0.023/GB/month | $0-5/month (deployment artifacts) | Minimal if just hosting frontend |
| **Lambda (Beyond Free)** | $0.20 per 1M requests + $0.0000166667 per GB-second | $0-2/month (low traffic) | Unlikely to exceed free tier in development |
| **DynamoDB (Beyond Free)** | $1.25/GB/month (on-demand writes/reads per request) | $0-1/month | Low traffic unlikely to exceed |

### Cost Optimization Tips

1. **Stay within free tier:** Configure CloudFront cache aggressively (leverage 30-90 day TTLs) to reduce requests
2. **Skip custom domain initially:** Use CloudFront domain (`{cf-domain}.cloudfront.net`) until necessary
3. **Use on-demand DynamoDB:** Already configured; scales with usage
4. **Monitor CloudFront costs:** Data transfer is the largest cost; use CloudFront functions to minimize unnecessary forwarding
5. **Lambda memory:** Default 128 MB usually sufficient; increase only if needed
6. **No VPC:** Current setup avoids NAT gateway ($32/month each)

### Estimated Monthly Cost (Development Environment)

**Scenario:** 1,000 users, each making 5 API calls/day (~150K API calls/month)

```
├─ Lambda:        Free tier covers (< 400K GB-seconds)
├─ API Gateway:   Free tier covers (< 750K calls)  
├─ DynamoDB:      Free tier covers (< 25 GB storage + requests)
├─ CloudFront:    ~$1-5 (data transfer)
├─ Route53:       $0 (unless custom domain: +$0.50)
├─ CloudWatch:    Free tier covers
├─ IAM:           Free
└─ S3:            Free tier covers

**Total: ~$1-5/month** (within free tier; Route53 optional +$0.50)
```

**Scenario:** 10,000 users, each making 10 API calls/day (~3M API calls/month)

```
├─ Lambda:        ~$0.50 (exceeds free tier slightly)
├─ API Gateway:   ~$1.05 (exceeds free tier)
├─ DynamoDB:      ~$1-3 (provisioned writes/reads)
├─ CloudFront:    ~$10-30 (data transfer to 10K users)
├─ Route53:       $0.50 (if using custom domain)
├─ CloudWatch:    Free tier covers
├─ IAM:           Free
└─ S3:            <$1 (storage)

**Total: ~$13-36/month**
```

### Free Tier Expiration

AWS free tier includes:
- **12 months free:** S3, some data transfer
- **Always free:** Lambda (1M requests), API Gateway (750K calls), DynamoDB (on-demand, 25GB), CloudWatch Logs (5GB), IAM
- **Promoted free:** CloudFront (10TB + 10M requests/month for new customers)

After free tier expires or usage exceeds limits:
- **Development environment** will likely remain <$10/month
- **Production environment** ranges $20-100+/month depending on traffic

### Reducing Costs Further

1. **Consolidate services:** Fewer API Gateway endpoints = fewer HTTP origins in CloudFront (each origin has small overhead)
2. **Enable caching:** Set `Cache-Control: max-age=3600` on CloudFront responses to reduce origin requests
3. **Lambda optimization:** 
   - Minimize package size (reduce data transfer)
   - Use provisioned concurrency only if cold starts are critical ($0.015/hour per concurrent execution)
4. **DynamoDB:** On-demand is already low-cost; switch to provisioned only if exceeding on-demand costs by 2x+
5. **Monitor dashboards:** Use AWS Cost Explorer to track daily spending

---

## Troubleshooting

### Bootstrap Issues

**Q: "Access to bucket was denied" during bootstrap**

```
Error: creating S3 bucket: operation error S3: CreateBucket, ...
```

**A:** Check AWS profile and credentials:
```bash
AWS_PROFILE=my-profile aws sts get-caller-identity
```

Ensure credentials have S3, DynamoDB, and IAM permissions.

**Q: "Bucket already exists but can't access it"**

**A:** Another AWS account may own the bucket (bucket names are globally unique). Create a bootstrap state bucket with a different suffix:

```bash
# Edit terraform/bootstrap/main.tf
# Change: "{project-name}-terraform-state-${data.aws_caller_identity.current.account_id}"
# To: "{custom-prefix}-terraform-state-${data.aws_caller_identity.current.account_id}"
```

### Foundation Deployment Issues

**Q: CloudFront distribution creation times out**

```
Error: ResourceInUseException: Resource in use
```

**A:** CloudFront distributions can take 10-15 minutes to fully create. Retry:
```bash
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation apply
```

**Q: Custom domain shows "Certificate pending"**

**A:** ACM certificate validation pending. If using email validation, check your email (or use DNS validation in ACM console). DNS validation usually resolves automatically within 5 minutes.

### Service Deployment Issues

**Q: "service-endpoints.auto.tfvars.json" doesn't exist**

```
Error: failed to read file: service-endpoints.auto.tfvars.json
```

**A:** Foundation hasn't been deployed, or first service wiring hasn't completed. Ensure:
```bash
AWS_PROFILE=my-profile scripts/setup-infra.sh dev
AWS_PROFILE=my-profile scripts/deploy-service.sh {service-name} dev  # ← Creates auto.tfvars.json
```

**Q: Service deployed but not accessible via CloudFront**

**A:** Check service is wired:
```bash
# View wired services
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation output wired_services

# If service missing, re-apply foundation
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation apply
```

**Q: "state lock acquired" error**

```
Error: resource state locked by another process
```

**A:** Another deployment is in progress, or lock stuck. Wait 10+ minutes, then check:
```bash
# Manually unlock (use with caution!)
aws dynamodb delete-item \
  --table-name {project-name}-terraform-locks \
  --key "{\"LockID\": {\"S\": \"{lock_id}\"}}" \
  --profile my-profile
```

Obtain `{lock_id}` from error message or CloudWatch logs.

### CORS & Request Issues

**Q: Frontend requests to API return 403 CORS error**

```
Access to XMLHttpRequest blocked by CORS policy
```

**A:** Verify `CORS_ORIGINS` env var on Lambda:
```bash
# Check Lambda env vars via AWS console or:
AWS_PROFILE=my-profile aws lambda get-function-configuration --function-name {function-name} --query Environment
```

Should include CloudFront URL:
```
CORS_ORIGINS=https://{cf-domain}.cloudfront.net,http://localhost:3000
```

If missing, service didn't read from foundation state properly. Re-apply service:
```bash
AWS_PROFILE=my-profile terraform -chdir=terraform/services/{service-name} apply
```

**Q: "Invalid origin verification" / 403 error**

```
x-origin-verify header invalid
```

**A:** CloudFront origin verification secret mismatch:
```bash
# Check service secret
AWS_PROFILE=my-profile terraform -chdir=terraform/services/{service-name} output origin_verify_secret

# Verify foundation has same secret in wired_services
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation output wired_services
```

If mismatch, re-apply service to refresh secret:
```bash
AWS_PROFILE=my-profile scripts/deploy-service.sh {service-name} dev
```

### Lambda & API Gateway Issues

**Q: "Function code size too large"**

```
Error: Deployment package too large
```

**A:** Lambda package exceeds 250 MB limit (or 50 MB zipped). Solutions:
- Remove unnecessary dependencies
- Use Lambda layers for large libraries
- Use custom Docker image (no size limit)

**Q: "Lambda function timeout"**

**A:** Increase `lambda_timeout` variable:
```bash
AWS_PROFILE=my-profile terraform -chdir=terraform/services/{service-name} apply \
  -var="lambda_timeout=120"  # ← 120 seconds
```

**Q: "API Gateway resource limit exceeded"**

```
LimitExceededException: Cannot create resource
```

**A:** API Gateway has 10,000 resource limit. This is rare; contact AWS support if hit.

### IAM & Permissions Issues

**Q: "User is not authorized to perform: dynamodb:GetItem"**

**A:** Lambda role missing user profiles table policy. Re-apply service:
```bash
AWS_PROFILE=my-profile terraform -chdir=terraform/services/{service-name} apply
```

Alternatively, manually attach policy:
```bash
aws iam attach-role-policy \
  --role-name {project-name}-{service-name}-{env}-lambda-role \
  --policy-arn $(AWS_PROFILE=my-profile terraform -chdir=terraform/foundation output -raw user_profiles_access_policy_arn)
```

### State & Backend Issues

**Q: "Backend initialization required"**

```
Error: Backend reinitialization required.
```

**A:** Backend config changed. Run init:
```bash
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation init -reconfigure
```

**Q: "Error reading object" from S3 state bucket**

**A:** S3 bucket deleted or permission removed. Check:
```bash
AWS_PROFILE=my-profile aws s3 ls s3://{project-name}-terraform-state-$(aws sts get-caller-identity --query Account --output text --profile my-profile)
```

If bucket gone, re-bootstrap (data loss):
```bash
AWS_PROFILE=my-profile scripts/bootstrap.sh
```

---

## Cleanup & Removal

### Destroy a Single Service

Removes service API Gateway, Lambda, and CloudFront origin. Preserves other services.

```bash
# Step 1: Destroy service terraform
AWS_PROFILE=my-profile terraform -chdir=terraform/services/{service-name} destroy

# Step 2: Remove service entry from service-endpoints.auto.tfvars.json
# Edit: terraform/foundation/service-endpoints.auto.tfvars.json
# Delete: "{service-name}" entry

# Step 3: Re-apply foundation (origin removed)
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation apply
```

Or use a script:
```bash
# Remove service from JSON
jq 'del(.api_services["{service-name}"])' \
  terraform/foundation/service-endpoints.auto.tfvars.json \
  > /tmp/endpoints.json && \
  mv /tmp/endpoints.json terraform/foundation/service-endpoints.auto.tfvars.json

# Destroy service
AWS_PROFILE=my-profile terraform -chdir=terraform/services/{service-name} destroy

# Re-apply foundation
AWS_PROFILE=my-profile terraform -chdir=terraform/foundation apply
```

### Destroy Foundation (All Services + Infrastructure)

Removes CloudFront, S3 frontend bucket, user profiles table, Route53. Preserves bootstrap state.

```bash
# Destroy all services first
for service in terraform/services/*/; do
  service_name=$(basename "$service")
  [[ "$service_name" == "_template" ]] && continue
  terraform -chdir="$service" destroy
done

# Remove all service entries from service-endpoints.auto.tfvars.json
echo '{"api_services":{}}' > terraform/foundation/service-endpoints.auto.tfvars.json

# Destroy foundation
terraform -chdir=terraform/foundation destroy
```

**Warning:** Destroys S3 frontend bucket. Backup assets if needed.

### Complete Wipe (Including Bootstrap)

Removes all infrastructure. AWS account returns to pre-terraform state.

```bash
# Step 1: Destroy all services
for service in terraform/services/*/; do
  service_name=$(basename "$service")
  [[ "$service_name" == "_template" ]] && continue
  terraform -chdir="$service" destroy
done

# Step 2: Destroy foundation
terraform -chdir=terraform/foundation destroy

# Step 3: Destroy bootstrap (removes S3 state bucket and DynamoDB locks table)
AWS_PROFILE=my-profile terraform -chdir=terraform/bootstrap destroy

# Optional Step 4: Delete state bucket manually (if destroy fails)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile my-profile)
aws s3 rb s3://{project-name}-terraform-state-${ACCOUNT_ID} --force --profile my-profile
```

**Warning:** This removes all terraform state. Any `terraform apply` after this rebuilds everything from scratch.

### Cleanup Order

Always destroy in reverse order of creation:

```
Services → Foundation → Bootstrap
```

**Reason:** Services depend on foundation outputs (terraform_remote_state). Destroying foundation first leaves services unable to refresh state.

---

## Reference: File Structure

```
terraform/
├── README.md                           ← This file
├── bootstrap/
│   ├── main.tf                         ← S3 + DynamoDB setup
│   ├── outputs.tf
│   ├── versions.tf
│   └── terraform.tfstate               ← Local state (after bootstrap)
├── foundation/
│   ├── main.tf                         ← CloudFront, S3, DynamoDB, Route53
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   ├── terraform.tfvars                ← Edit for custom domain, project name
│   ├── prod.tfvars                     ← (Optional) Production overrides
│   ├── service-endpoints.auto.tfvars.json  ← Auto-generated by deploy-service.sh
│   └── .terraform/                     ← Terraform cache (safe to delete)
└── services/
    ├── _template/                      ← Template for new services
    │   ├── README.md
    │   ├── main.tf.tmpl
    │   ├── variables.tf.tmpl
    │   ├── outputs.tf.tmpl
    │   └── versions.tf.tmpl
    ├── twin-api/                       ← Example: LLM endpoint
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   ├── versions.tf
    │   ├── terraform.tfvars
    │   └── .terraform/
    ├── trading-api/                    ← Example: Trading operations
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   ├── versions.tf
    │   ├── terraform.tfvars
    │   └── .terraform/
    └── stock-scraper-api/              ← Example: Stock data
        ├── main.tf
        ├── variables.tf
        ├── outputs.tf
        ├── versions.tf
        ├── terraform.tfvars
        └── .terraform/
```

---

## Regional Configuration

Default region is set in `versions.tf` files. Common regions:
- `ap-south-1` (Asia-Pacific: Mumbai, India)
- `us-east-1` (US: N. Virginia)
- `us-west-2` (US: Oregon)
- `eu-west-1` (Europe: Ireland)
- `eu-central-1` (Europe: Frankfurt)
- `ap-southeast-1` (Asia-Pacific: Singapore)

To change regions globally:

```bash
# Edit each versions.tf file
terraform/bootstrap/versions.tf
terraform/foundation/versions.tf
terraform/services/*/versions.tf

# Change: region = "{current-region}" → region = "{new-region}"
# Example: region = "ap-south-1" → region = "us-west-2"
```

**Important:** `foundation/versions.tf` requires **two** provider blocks:
- Primary region (your choice)
- `us-east-1` alias (required for CloudFront ACM certificates)

---

## Support & Contributing

For issues or improvements:

- Check the [Troubleshooting](#troubleshooting) section
- Review Terraform state: `AWS_PROFILE=my-profile terraform -chdir=terraform/{module} show`
- Check CloudWatch logs: `AWS_PROFILE=my-profile aws logs tail /aws/lambda/{function-name} --follow`
- Validate HCL: `AWS_PROFILE=my-profile terraform -chdir=terraform/{module} validate`

---

**Last Updated:** March 2026  
**Terraform Version:** >= 1.0  
**AWS Provider Version:** ~> 6.0
