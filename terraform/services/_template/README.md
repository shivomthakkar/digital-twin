# Adding a New Service

Follow these steps to add a fully independent deployable service.

## 1. Copy the template

```bash
cp -r terraform/services/_template terraform/services/my-service
# Rename .tmpl extensions
for f in terraform/services/my-service/*.tmpl; do mv "$f" "${f%.tmpl}"; done
```

## 2. Fill in the REPLACE markers

Search for `# REPLACE:` in the four files and update each one:

| File | What to change |
|---|---|
| `main.tf` | `local.service_name`, Lambda filename/handler/runtime, routes, IAM policies |
| `variables.tf` | Add service-specific variables (keep contract section verbatim) |
| `outputs.tf` | `service_name` value must match your service folder name |
| `versions.tf` | No changes needed — the key is injected by the script |

## 3. Add a terraform.tfvars

Create `terraform/services/my-service/terraform.tfvars` with static defaults (no environment-specific values):

```hcl
project_name   = "twin"
lambda_timeout = 30
```

## 4. Add the Lambda build step

In `scripts/deploy-service.sh`, add a new `elif` branch:

```bash
elif [[ "$SERVICE" == "my-service" ]]; then
  echo "Building my-service Lambda..."
  (cd my-service-dir && <build command>)
```

## 5. Register the service API URL in the frontend

`deploy-frontend.sh` auto-discovers all services under `terraform/services/`,
inits each module against its S3 state, and reads `api_gateway_url` + `service_name`
directly via `terraform output`. The `NEXT_PUBLIC_*` env var is derived automatically:
- `my-service-api` → `NEXT_PUBLIC_MY_SERVICE_API_URL`
- `trading-api`    → `NEXT_PUBLIC_TRADING_API_URL`

**No edits to any script needed when adding a new service.**

`cors_origins` is also wired automatically from foundation state via
`data.terraform_remote_state.foundation` — no variable injection needed.

## 6. Deploy

```bash
# First time only (or after any terraform change)
scripts/deploy-service.sh my-service dev

# Frontend picks up the new service URL automatically
scripts/deploy-frontend.sh dev
```

## Service Contract Summary

| Interface | Name | Direction |
|---|---|---|
| Input variable | `cors_origins` | foundation → service (via script) |
| Output | `api_gateway_url` | service → frontend (via script) |
| Output | `service_name` | service → script dispatch + env var naming |
