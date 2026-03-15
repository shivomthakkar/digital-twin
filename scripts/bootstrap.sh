#!/bin/bash
# bootstrap.sh — Run ONCE per AWS account.
# Creates the S3 state bucket and DynamoDB lock table used by all terraform modules.
# Idempotent: safe to re-run if the bucket already exists.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT/terraform/bootstrap"

echo "🔧 Checking bootstrap prerequisites..."

AWS_PROFILE="${AWS_PROFILE:-terraform}"
ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
STATE_BUCKET="twin-terraform-state-${ACCOUNT_ID}"

# Idempotency check — skip apply if bucket already exists
if aws s3api head-bucket --bucket "$STATE_BUCKET" --profile "$AWS_PROFILE" 2>/dev/null; then
  echo "✅ State bucket '$STATE_BUCKET' already exists — bootstrap already complete."
  echo "   DynamoDB table : twin-terraform-locks"
  echo "   State bucket   : $STATE_BUCKET"
  exit 0
fi

echo "🚀 Bootstrapping Terraform state infrastructure..."
echo "   Account ID     : $ACCOUNT_ID"
echo "   State bucket   : $STATE_BUCKET"
echo ""

terraform -chdir="$TF_DIR" init -input=false
terraform -chdir="$TF_DIR" apply -auto-approve

echo ""
echo "✅ Bootstrap complete!"
echo "   State bucket   : $(terraform -chdir="$TF_DIR" output -raw state_bucket_name)"
echo "   DynamoDB table : $(terraform -chdir="$TF_DIR" output -raw dynamodb_table_name)"
echo ""
echo "Next step: scripts/setup-infra.sh <env>"
