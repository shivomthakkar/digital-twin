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
# CONTRACT VARIABLES — Cognito auth (copy to every service)
# ===========================================================================

variable "enable_cognito_auth" {
  description = "Attach a Cognito JWT authorizer to the $default catch-all route. Set cognito_user_pool_id and cognito_app_client_id when enabling."
  type        = bool
  default     = false
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID (e.g. ap-south-1_XXXXXXXXX). Required when enable_cognito_auth=true."
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

# ===========================================================================
# Dhanhq configuration — sandbox or prod mode
# ===========================================================================

variable "dhan_mode" {
  description = "Dhan broker API mode: 'sandbox' or 'prod'. Passed to deploy.py to patch dhanhq base_url."
  type        = string
  default     = "sandbox"
  validation {
    condition     = contains(["sandbox", "prod"], var.dhan_mode)
    error_message = "dhan_mode must be either 'sandbox' or 'prod'."
  }
}
