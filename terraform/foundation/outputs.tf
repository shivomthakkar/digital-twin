output "cloudfront_url" {
  description = "HTTPS URL of the CloudFront distribution"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (used for cache invalidations)"
  value       = aws_cloudfront_distribution.main.id
}

output "s3_frontend_bucket" {
  description = "S3 bucket name for frontend static assets"
  value       = aws_s3_bucket.frontend.id
}

# cors_origins is a computed convenience output consumed by service deploys.
# It contains the exact value to set as CORS_ORIGINS on each Lambda so that
# requests from the frontend are permitted.
output "cors_origins" {
  description = "Allowed CORS origins derived from the live frontend URL (always includes localhost:3000 for local dev)"
  value = var.use_custom_domain && var.root_domain != "" ? join(",", [
    "https://${var.root_domain}",
    "https://www.${var.root_domain}",
    "http://localhost:3000"
  ]) : join(",", [
    "https://${aws_cloudfront_distribution.main.domain_name}",
    "http://localhost:3000"
  ])
}

output "custom_domain_url" {
  description = "Custom domain URL (empty string when use_custom_domain=false)"
  value       = var.use_custom_domain ? "https://${var.root_domain}" : ""
}

# Set these 4 nameservers at your domain registrar to point your domain at
# this Route53 hosted zone. Only populated when use_custom_domain=true.
output "route53_name_servers" {
  description = "NS records to configure at your domain registrar"
  value       = var.use_custom_domain ? aws_route53_zone.root[0].name_servers : []
}

output "use_custom_domain" {
  description = "Whether a custom domain is attached"
  value       = var.use_custom_domain
}

output "root_domain" {
  description = "Root domain name (empty string when use_custom_domain=false)"
  value       = var.root_domain
}

output "wired_services" {
  description = "Map of service name → { gateway_url, path_prefixes } for services currently wired as CloudFront origins (no secrets exposed)"
  value       = { for k, v in local.active_services : k => { gateway_url = v.gateway_url, path_prefixes = v.path_prefixes } }
}

output "user_profiles_table_name" {
  description = "DynamoDB table name for user profiles — set as USER_PROFILES_TABLE env var in services"
  value       = aws_dynamodb_table.user_profiles.name
}

output "user_profiles_table_arn" {
  description = "ARN of the user profiles DynamoDB table"
  value       = aws_dynamodb_table.user_profiles.arn
}

output "user_profiles_access_policy_arn" {
  description = "ARN of the IAM policy granting GetItem/PutItem/UpdateItem on the user profiles table — attach to service Lambda roles"
  value       = aws_iam_policy.user_profiles_access.arn
}
