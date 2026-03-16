# ===========================================================================
# CONTRACT VARIABLES
# ===========================================================================

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, prod."
  }
}

# ===========================================================================
# SERVICE-SPECIFIC VARIABLES
# ===========================================================================

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 10
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit (req/s)"
  type        = number
  default     = 5
}

variable "enable_origin_protection" {
  description = "Create a WAF WebACL that blocks direct API Gateway access (only CloudFront with the correct x-origin-verify header is allowed). NOTE: costs money."
  type        = bool
  default     = false
}

# ===========================================================================
# CONTRACT VARIABLES — Cognito auth
# ===========================================================================

variable "enable_cognito_auth" {
  description = "Attach a Cognito JWT authorizer to the $default catch-all route."
  type        = bool
  default     = false
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID (e.g. us-east-1_XXXXXXXXX). Required when enable_cognito_auth=true."
  type        = string
  default     = null
}

variable "cognito_app_client_id" {
  description = "Cognito App Client ID. Required when enable_cognito_auth=true."
  type        = string
  default     = null
}

variable "cognito_region" {
  description = "AWS region where the Cognito User Pool lives."
  type        = string
  default     = "us-east-1"
}
