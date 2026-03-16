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
  value       = "stock-scraper-api"
}

locals {
  _pub_f           = data.terraform_remote_state.foundation.outputs
  _pub_cf_base     = try(local._pub_f.custom_domain_url, "") != "" ? local._pub_f.custom_domain_url : try(local._pub_f.cloudfront_url, "")
  _wired_entry     = try(local._pub_f.wired_services["stock-scraper-api"], null)
  _pub_is_wired    = local._wired_entry != null && try(local._wired_entry.gateway_url, "") == aws_apigatewayv2_api.main.api_endpoint
  _pub_path_prefix = local._pub_is_wired ? try(local._wired_entry.path_prefixes[0], "") : ""
}

output "public_url" {
  description = "Canonical public-facing URL: CloudFront + path prefix when wired to CF, direct API Gateway URL otherwise"
  value       = local._pub_is_wired ? "${trimsuffix(local._pub_cf_base, "/")}${local._pub_path_prefix}" : aws_apigatewayv2_api.main.api_endpoint
}

output "origin_verify_secret" {
  description = "Secret value that CloudFront sends as x-origin-verify header."
  value       = random_password.origin_secret.result
  sensitive   = true
}

# ===========================================================================
# SERVICE-SPECIFIC OUTPUTS
# ===========================================================================

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "dynamodb_table_financials" {
  description = "DynamoDB table for stock financial data"
  value       = aws_dynamodb_table.stock_financials.name
}

output "dynamodb_table_documents" {
  description = "DynamoDB table for stock documents"
  value       = aws_dynamodb_table.stock_documents.name
}

output "dynamodb_table_sections" {
  description = "DynamoDB table for stock section tables"
  value       = aws_dynamodb_table.stock_sections.name
}
