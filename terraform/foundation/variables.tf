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

variable "api_gateway_url" {
  description = "HTTPS base URL of the API Gateway to expose via CloudFront. Auto-written to service-endpoints.auto.tfvars by deploy-service.sh."
  type        = string
  default     = ""
}

variable "api_path_prefixes" {
  description = "List of path prefixes to route to the API Gateway (e.g. [\"/api\", \"/v2\"]). Each prefix gets its own CloudFront cache behavior and the prefix is stripped before forwarding. Auto-written by deploy-service.sh."
  type        = list(string)
  default     = ["/api"]
  validation {
    condition     = alltrue([for p in var.api_path_prefixes : startswith(p, "/")])
    error_message = "Every api_path_prefix must start with '/'"
  }
}

variable "origin_verify_secret" {
  description = "Secret sent as x-origin-verify header from CloudFront to API Gateway to prove requests originate from the CDN. Auto-written by deploy-service.sh."
  type        = string
  default     = ""
  sensitive   = true
}
