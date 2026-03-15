# ===========================================================================
# CONTRACT OUTPUTS — copy this section verbatim into every new service.
# deploy-frontend.sh sources these to build NEXT_PUBLIC_* env vars.
# ===========================================================================

output "api_gateway_url" {
  description = "Base URL of this service's API Gateway endpoint"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "service_name" {
  description = "Canonical name of this service (used by scripts for dispatch and env var naming)"
  value       = "twin-api"
}

# Compute the canonical public URL: CloudFront + first path prefix when this
# service is wired to CF, otherwise the direct API Gateway URL.
# deploy-service.sh runs `terraform apply -refresh-only` after wiring CF to
# ensure this value is up-to-date in state before deploy-frontend.sh reads it.
locals {
  _pub_f           = data.terraform_remote_state.foundation.outputs
  _pub_cf_base     = try(local._pub_f.custom_domain_url, "") != "" ? local._pub_f.custom_domain_url : try(local._pub_f.cloudfront_url, "")
  _pub_is_wired    = try(local._pub_f.attached_api_gateway_url, "") == aws_apigatewayv2_api.main.api_endpoint
  _pub_path_prefix = local._pub_is_wired && length(try(local._pub_f.api_path_prefixes, [])) > 0 ? local._pub_f.api_path_prefixes[0] : ""
}

output "public_url" {
  description = "Canonical public-facing URL: CloudFront + path prefix when wired to CF, direct API Gateway URL otherwise"
  value       = local._pub_is_wired ? "${trimsuffix(local._pub_cf_base, "/")}${local._pub_path_prefix}" : aws_apigatewayv2_api.main.api_endpoint
}

output "origin_verify_secret" {
  description = "Secret value that CloudFront sends as x-origin-verify header to prove requests originate from the CDN. Read by deploy-service.sh to wire up the CloudFront origin."
  value       = random_password.origin_secret.result
  sensitive   = true
}

# ===========================================================================
# SERVICE-SPECIFIC OUTPUTS
# ===========================================================================

output "lambda_function_name" {
  description = "Lambda function name (useful for log tailing and manual invocations)"
  value       = aws_lambda_function.api.function_name
}

output "s3_memory_bucket" {
  description = "S3 bucket storing conversation history"
  value       = aws_s3_bucket.memory.id
}
