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

variable "use_custom_domain" {
  description = "Attach a custom domain to CloudFront"
  type        = bool
  default     = false
}

variable "root_domain" {
  description = "Apex domain name, e.g. mydomain.com (required when use_custom_domain=true)"
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# API Gateway CloudFront integration — auto-populated by deploy-service.sh
# ---------------------------------------------------------------------------

variable "api_services" {
  description = "Map of service name → endpoint config. Managed by deploy-service.sh via service-endpoints.auto.tfvars.json. Adding a new service requires no changes here."
  type = map(object({
    gateway_url   = string
    verify_secret = string
    path_prefixes = list(string)
  }))
  default = {}
}
