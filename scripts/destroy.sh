#!/bin/bash
# destroy.sh <scope> <env> [service]
# Tears down terraform infrastructure for a given scope + environment.
#
# Scopes:
#   --service <name> <env>   Destroy one service only (e.g. twin-api)
#   --foundation <env>       Destroy foundation (must destroy all services first)
#   --all <env>              Destroy all known services, then foundation
#
# Usage:
#   scripts/destroy.sh --service twin-api dev
#   scripts/destroy.sh --foundation dev
#   scripts/destroy.sh --all dev
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "❌ Usage:"
  echo "   $0 --service <service> <env>"
  echo "   $0 --foundation <env>"
  echo "   $0 --all <env>"
  exit 1
fi

SCOPE="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AWS_PROFILE="${AWS_PROFILE:-terraform}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

get_account_id() {
  aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text
}

empty_bucket() {
  local BUCKET="$1"
  if aws s3 ls "s3://$BUCKET" --profile "$AWS_PROFILE" 2>/dev/null; then
    echo "  Emptying s3://$BUCKET..."
    aws s3 rm "s3://$BUCKET" --recursive --profile "$AWS_PROFILE"
  else
    echo "  Bucket not found or already empty: $BUCKET"
  fi
}

destroy_service() {
  local SERVICE="$1"
  local ENV="$2"
  local TF_DIR="$ROOT/terraform/services/${SERVICE}"

  if [[ ! -d "$TF_DIR" ]]; then
    echo "❌ Service not found: terraform/services/${SERVICE}"
    exit 1
  fi

  ACCOUNT_ID=$(get_account_id)
  STATE_BUCKET="twin-terraform-state-${ACCOUNT_ID}"

  echo ""
  echo "🗑️  Destroying service '${SERVICE}' in environment '${ENV}'..."

  terraform -chdir="$TF_DIR" init -input=false \
    -backend-config="bucket=${STATE_BUCKET}" \
    -backend-config="key=services/${SERVICE}/${ENV}/terraform.tfstate" \
    -backend-config="dynamodb_table=twin-terraform-locks" \
    -reconfigure

  # Read bucket name from state before destroying
  local MEMORY_BUCKET
  MEMORY_BUCKET=$(terraform -chdir="$TF_DIR" output -raw s3_memory_bucket 2>/dev/null || echo "")
  [[ -n "$MEMORY_BUCKET" ]] && empty_bucket "$MEMORY_BUCKET"

  terraform -chdir="$TF_DIR" destroy \
    -var="environment=${ENV}" \
    -auto-approve

  # Remove the auto.tfvars that wires this service into CloudFront so that a
  # subsequent setup-infra.sh run does not try to reference the deleted APIG.
  ENDPOINTS_TFVARS="$ROOT/terraform/foundation/service-endpoints.auto.tfvars"
  if [[ -f "$ENDPOINTS_TFVARS" ]]; then
    echo "  Removing foundation/service-endpoints.auto.tfvars..."
    rm "$ENDPOINTS_TFVARS"
  fi

  echo "✅ Service '${SERVICE}' destroyed."
}

destroy_foundation() {
  local ENV="$1"
  local TF_DIR="$ROOT/terraform/foundation"

  ACCOUNT_ID=$(get_account_id)
  STATE_BUCKET="twin-terraform-state-${ACCOUNT_ID}"

  echo ""
  echo "🗑️  Destroying foundation for environment '${ENV}'..."

  terraform -chdir="$TF_DIR" init -input=false \
    -backend-config="bucket=${STATE_BUCKET}" \
    -backend-config="key=foundation/${ENV}/terraform.tfstate" \
    -backend-config="dynamodb_table=twin-terraform-locks" \
    -reconfigure

  # Read bucket name from state before destroying
  local FRONTEND_BUCKET
  FRONTEND_BUCKET=$(terraform -chdir="$TF_DIR" output -raw s3_frontend_bucket 2>/dev/null || echo "")
  [[ -n "$FRONTEND_BUCKET" ]] && empty_bucket "$FRONTEND_BUCKET"

  terraform -chdir="$TF_DIR" destroy \
    -var="environment=${ENV}" \
    -auto-approve

  echo "✅ Foundation for '${ENV}' destroyed."
}

# ---------------------------------------------------------------------------
# Dispatch on scope
# ---------------------------------------------------------------------------

case "$SCOPE" in

  --service)
    if [[ $# -lt 3 ]]; then
      echo "❌ Usage: $0 --service <service> <env>"
      exit 1
    fi
    SERVICE="$2"
    ENV="$3"
    echo "⚠️  This will destroy service '${SERVICE}' in '${ENV}'. Ctrl-C to abort."
    sleep 3
    destroy_service "$SERVICE" "$ENV"
    ;;

  --foundation)
    ENV="$2"
    echo "⚠️  This will destroy the FOUNDATION for '${ENV}'."
    echo "   Ensure all services have been destroyed first."
    echo "   Ctrl-C to abort."
    sleep 3
    destroy_foundation "$ENV"
    ;;

  --all)
    ENV="$2"
    echo "⚠️  This will destroy ALL services + foundation for '${ENV}'. Ctrl-C to abort."
    sleep 3

    # Discover deployed services from terraform/services/ directory
    SERVICES=()
    for SERVICE_DIR in "$ROOT/terraform/services"/*/; do
      SVC=$(basename "$SERVICE_DIR")
      [[ "$SVC" == _* ]] && continue
      SERVICES+=("$SVC")
    done

    if [[ ${#SERVICES[@]} -eq 0 ]]; then
      echo "No services found in terraform/services/. Skipping service destruction."
    else
      for SVC in "${SERVICES[@]}"; do
        destroy_service "$SVC" "$ENV"
      done
    fi

    destroy_foundation "$ENV"
    echo ""
    echo "✅ All infrastructure for '${ENV}' destroyed."
    echo ""
    echo "💡 To remove the Terraform state bucket entirely (destroys all envs):"
    echo "   cd terraform/bootstrap && terraform destroy -auto-approve"
    ;;

  *)
    echo "❌ Unknown scope: $SCOPE"
    echo "   Use: --service <name> <env> | --foundation <env> | --all <env>"
    exit 1
    ;;
esac
