#!/bin/bash
# setup-infra.sh <env> [--domain <domain>]
# Deploys foundation infrastructure (CloudFront + frontend S3 + optional custom domain).
# Run once per environment, or re-run whenever foundation config changes.
# All outputs are stored in S3 terraform state and read directly by other scripts.
#
# Usage:
#   scripts/setup-infra.sh dev
#   scripts/setup-infra.sh prod --domain yourdomain.com
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "❌ Usage: $0 <environment> [--domain <domain>]"
  echo "   Environments: dev | test | prod"
  echo "   Example with custom domain: $0 prod --domain yourdomain.com"
  exit 1
fi

ENV="$1"
shift

# Parse optional --domain flag
DOMAIN=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    *)
      echo "❌ Unknown argument: $1"
      exit 1
      ;;
  esac
done
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT/terraform/foundation"

AWS_PROFILE="${AWS_PROFILE:-terraform}"
ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
STATE_BUCKET="twin-terraform-state-${ACCOUNT_ID}"
LOCK_TABLE="twin-terraform-locks"
STATE_KEY="foundation/${ENV}/terraform.tfstate"

echo "🏗️  Setting up foundation infrastructure for environment: ${ENV}"
[[ -n "$DOMAIN" ]] && echo "   Custom domain: ${DOMAIN}"
echo "   State: s3://${STATE_BUCKET}/${STATE_KEY}"
echo ""

# Extra var file for prod overrides (optional)
EXTRA_VARS=()
if [[ "$ENV" == "prod" && -f "$TF_DIR/prod.tfvars" ]]; then
  EXTRA_VARS=(-var-file="prod.tfvars")
fi

# Domain vars override terraform.tfvars when --domain is passed
if [[ -n "$DOMAIN" ]]; then
  EXTRA_VARS+=(-var="use_custom_domain=true" -var="root_domain=${DOMAIN}")
fi

terraform -chdir="$TF_DIR" init -input=false \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="key=${STATE_KEY}" \
  -backend-config="dynamodb_table=${LOCK_TABLE}" \
  -reconfigure

terraform -chdir="$TF_DIR" apply \
  -var="environment=${ENV}" \
  "${EXTRA_VARS[@]}" \
  -auto-approve

# Capture outputs for console display
CLOUDFRONT_URL=$(terraform -chdir="$TF_DIR" output -raw cloudfront_url)
CLOUDFRONT_ID=$(terraform -chdir="$TF_DIR" output -raw cloudfront_distribution_id)
FRONTEND_BUCKET=$(terraform -chdir="$TF_DIR" output -raw s3_frontend_bucket)
CORS_ORIGINS=$(terraform -chdir="$TF_DIR" output -raw cors_origins)
CUSTOM_URL=$(terraform -chdir="$TF_DIR" output -raw custom_domain_url 2>/dev/null || echo "")
NS_RECORDS=$(terraform -chdir="$TF_DIR" output -json route53_name_servers 2>/dev/null || echo "[]")

echo ""
echo "✅ Foundation deployed!"
echo "   CloudFront URL : ${CLOUDFRONT_URL}"
echo "   Frontend bucket: ${FRONTEND_BUCKET}"
echo "   CORS origins   : ${CORS_ORIGINS}"
[[ -n "$CUSTOM_URL" ]] && echo "   Custom domain  : ${CUSTOM_URL}"

if [[ "$NS_RECORDS" != "[]" && "$NS_RECORDS" != "" ]]; then
  echo ""
  echo "⚠️  ACTION REQUIRED — set these nameservers at your domain registrar:"
  echo "$NS_RECORDS" | tr -d '[]"' | tr ',' '\n' | sed 's/^ */   ns: /'
  echo ""
  echo "   ACM certificate validation will complete automatically once DNS propagates (~5 min)."
fi
echo ""
echo "All outputs stored in S3 state: s3://${STATE_BUCKET}/${STATE_KEY}"
echo ""
echo "Next steps:"
echo "  scripts/deploy-service.sh twin-api ${ENV}"
echo "  scripts/deploy-frontend.sh ${ENV}"
