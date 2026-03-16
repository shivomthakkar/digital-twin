#!/bin/bash
# deploy-service.sh <service> <env> [--paths /api /v2 ...]
# Builds the Lambda package for <service> and deploys its terraform module.
# cors_origins is read automatically from foundation S3 state via terraform_remote_state.
# All outputs stored in S3 state — no local files written.
#
# Usage:
#   scripts/deploy-service.sh twin-api dev
#   scripts/deploy-service.sh twin-api dev --paths /api
#   scripts/deploy-service.sh twin-api dev --paths /api /v2 /internal
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "❌ Usage: $0 <service> <environment> [--paths /prefix1 /prefix2 ...]"
  echo "   Example: $0 twin-api dev --paths /api"
  exit 1
fi

SERVICE="$1"
ENV="$2"
shift 2

# Per-service default path prefix (override with --paths flag)
case "$SERVICE" in
  twin-api)          _default_path="/api" ;;
  trading-api)       _default_path="/trading" ;;
  stock-scraper-api) _default_path="/real-time" ;;
  *)                 _default_path="/api" ;;
esac

# Parse optional --paths flag; defaults to service-specific prefix when not supplied
API_PATHS=("$_default_path")
if [[ $# -gt 0 && "$1" == "--paths" ]]; then
  shift
  API_PATHS=()
  while [[ $# -gt 0 && "$1" != --* ]]; do
    API_PATHS+=("$1")
    shift
  done
  if [[ ${#API_PATHS[@]} -eq 0 ]]; then
    echo "❌ --paths requires at least one path prefix (e.g. /api)"
    exit 1
  fi
fi

# Serialise the paths array to a Terraform-compatible JSON list string, e.g. ["/api","/v2"]
API_PATHS_JSON="["
for i in "${!API_PATHS[@]}"; do
  [[ $i -gt 0 ]] && API_PATHS_JSON+=","
  API_PATHS_JSON+="\"${API_PATHS[$i]}\""
done
API_PATHS_JSON+="]"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT/terraform/services/${SERVICE}"

# Validate service directory exists
if [[ ! -d "$TF_DIR" ]]; then
  echo "❌ Service directory not found: $TF_DIR"
  exit 1
fi

# jq is required for merging service-endpoints.auto.tfvars.json
if ! command -v jq &>/dev/null; then
  echo "❌ jq is required but not installed."
  echo "   macOS: brew install jq  |  Ubuntu: apt-get install jq"
  exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
STATE_BUCKET="twin-terraform-state-${ACCOUNT_ID}"
LOCK_TABLE="twin-terraform-locks"
STATE_KEY="services/${SERVICE}/${ENV}/terraform.tfstate"

echo "🚀 Deploying service '${SERVICE}' to environment '${ENV}'"
echo "   State          : s3://${STATE_BUCKET}/${STATE_KEY}"
echo ""

# ---------------------------------------------------------------------------
# Lambda build dispatch — add an elif block for each new service
# ---------------------------------------------------------------------------
echo "📦 Building Lambda package for ${SERVICE}..."

if [[ "$SERVICE" == "twin-api" ]]; then
  (cd "$ROOT/backend" && uv run deploy.py)

elif [[ "$SERVICE" == "trading-api" ]]; then
  (cd "$ROOT/trading" && uv run deploy.py)

elif [[ "$SERVICE" == "stock-scraper-api" ]]; then
  (cd "$ROOT/stock_scraper" && uv run deploy.py)

else
  echo "❌ No build step defined for service '${SERVICE}'."
  echo "   Add an 'elif' block in scripts/deploy-service.sh."
  exit 1
fi

echo "✅ Lambda package built."
echo ""

# ---------------------------------------------------------------------------
# Terraform apply
# ---------------------------------------------------------------------------

# Extra var file for prod overrides (optional)
EXTRA_VARS=()
if [[ "$ENV" == "prod" && -f "$TF_DIR/prod.tfvars" ]]; then
  EXTRA_VARS=(-var-file="prod.tfvars")
fi

# Cognito auth vars — only injected when the corresponding env vars are set.
# Usage: ENABLE_COGNITO_AUTH=true COGNITO_USER_POOL_ID=us-east-1_XXX COGNITO_APP_CLIENT_ID=XXX scripts/deploy-service.sh twin-api dev
COGNITO_VARS=()
[[ -n "${ENABLE_COGNITO_AUTH:-}" ]]   && COGNITO_VARS+=(-var="enable_cognito_auth=${ENABLE_COGNITO_AUTH}")
[[ -n "${COGNITO_USER_POOL_ID:-}" ]]  && COGNITO_VARS+=(-var="cognito_user_pool_id=${COGNITO_USER_POOL_ID}")
[[ -n "${COGNITO_APP_CLIENT_ID:-}" ]] && COGNITO_VARS+=(-var="cognito_app_client_id=${COGNITO_APP_CLIENT_ID}")
[[ -n "${COGNITO_REGION:-}" ]]        && COGNITO_VARS+=(-var="cognito_region=${COGNITO_REGION}")

terraform -chdir="$TF_DIR" init -input=false \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="key=${STATE_KEY}" \
  -backend-config="dynamodb_table=${LOCK_TABLE}" \
  -reconfigure

terraform -chdir="$TF_DIR" apply \
  -var="environment=${ENV}" \
  "${EXTRA_VARS[@]+"${EXTRA_VARS[@]}"}" \
  "${COGNITO_VARS[@]+"${COGNITO_VARS[@]}"}" \
  -auto-approve

# Capture contract outputs for console display
API_GATEWAY_URL=$(terraform -chdir="$TF_DIR" output -raw api_gateway_url)
SERVICE_NAME=$(terraform -chdir="$TF_DIR" output -raw service_name)
LAMBDA_FUNCTION_NAME=$(terraform -chdir="$TF_DIR" output -raw lambda_function_name 2>/dev/null || echo "")
ORIGIN_SECRET=$(terraform -chdir="$TF_DIR" output -raw origin_verify_secret 2>/dev/null || echo "")

echo ""
echo "✅ Service '${SERVICE}' deployed!"
echo "   API Gateway URL: ${API_GATEWAY_URL}"
[[ -n "$LAMBDA_FUNCTION_NAME" ]] && echo "   Lambda function: ${LAMBDA_FUNCTION_NAME}"
echo ""

# ---------------------------------------------------------------------------
# Wire up CloudFront origin — re-apply foundation with this service's APIG URL
# ---------------------------------------------------------------------------

if [[ -n "$ORIGIN_SECRET" && -n "$API_GATEWAY_URL" ]]; then
  FOUNDATION_TF="$ROOT/terraform/foundation"
  ENDPOINTS_JSON="$FOUNDATION_TF/service-endpoints.auto.tfvars.json"

  echo "🔗 Wiring API Gateway to CloudFront..."
  echo "   Merging into ${ENDPOINTS_JSON}"

  # Migrate: remove old single-service HCL file if still present
  rm -f "$FOUNDATION_TF/service-endpoints.auto.tfvars"

  # Read existing JSON (or start empty), then merge this service's entry in.
  # Other services' entries are preserved unchanged.
  EXISTING=$(cat "$ENDPOINTS_JSON" 2>/dev/null || echo '{"api_services":{}}')
  jq --arg key "$SERVICE" \
     --arg url "$API_GATEWAY_URL" \
     --arg secret "$ORIGIN_SECRET" \
     --argjson paths "$API_PATHS_JSON" \
     '.api_services[$key] = { "gateway_url": $url, "verify_secret": $secret, "path_prefixes": $paths }' \
     <<< "$EXISTING" > "$ENDPOINTS_JSON"

  terraform -chdir="$FOUNDATION_TF" init -input=false \
    -backend-config="bucket=${STATE_BUCKET}" \
    -backend-config="key=foundation/${ENV}/terraform.tfstate" \
    -backend-config="dynamodb_table=${LOCK_TABLE}" \
    -reconfigure -no-color > /dev/null

  # Read domain config from existing state so a re-apply never clobbers it
  USE_CUSTOM_DOMAIN=$(terraform -chdir="$FOUNDATION_TF" output -raw use_custom_domain 2>/dev/null || echo "false")
  ROOT_DOMAIN=$(terraform -chdir="$FOUNDATION_TF" output -raw root_domain 2>/dev/null || echo "")

  terraform -chdir="$FOUNDATION_TF" apply \
    -var="environment=${ENV}" \
    -var="use_custom_domain=${USE_CUSTOM_DOMAIN}" \
    -var="root_domain=${ROOT_DOMAIN}" \
    -auto-approve

  CF_URL=$(terraform -chdir="$FOUNDATION_TF" output -raw cloudfront_url 2>/dev/null || echo "")
  CUSTOM_URL=$(terraform -chdir="$FOUNDATION_TF" output -raw custom_domain_url 2>/dev/null || echo "")
  CANONICAL_BASE="${CUSTOM_URL:-$CF_URL}"
  CANONICAL_BASE="${CANONICAL_BASE%/}"
  PUBLIC_URL="${CANONICAL_BASE}${API_PATHS[0]}"
  echo "✅ CloudFront updated — public endpoint: ${PUBLIC_URL}"
  echo ""

  # Refresh service state so public_url output reflects the new CF wiring.
  # deploy-frontend.sh reads public_url from this state, so it must be current.
  echo "🔄 Refreshing service state (updating public_url)..."
  terraform -chdir="$TF_DIR" apply -refresh-only \
    -var="environment=${ENV}" \
    "${EXTRA_VARS[@]+"${EXTRA_VARS[@]}"}" \
    -auto-approve -no-color > /dev/null
  echo ""
fi

echo "All outputs stored in S3 state: s3://${STATE_BUCKET}/${STATE_KEY}"
echo ""
echo "Next step: scripts/deploy-frontend.sh ${ENV}"
