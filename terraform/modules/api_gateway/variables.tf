# =============================================================================
# FinSight AI - API Gateway Module Variables
# =============================================================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "finsight-ai"
}

variable "stage_name" {
  description = "API Gateway deployment stage name"
  type        = string
  default     = "prod"
}

# -----------------------------------------------------------------------------
# Lambda Integration
# -----------------------------------------------------------------------------
variable "rag_query_handler_invoke_arn" {
  description = "Invoke ARN of the rag_query_handler Lambda function"
  type        = string
}

variable "rag_query_handler_function_name" {
  description = "Name of the rag_query_handler Lambda function"
  type        = string
}

# -----------------------------------------------------------------------------
# Rate Limiting & Quotas
# -----------------------------------------------------------------------------
variable "throttle_burst_limit" {
  description = "Maximum number of concurrent requests (burst)"
  type        = number
  default     = 100
}

variable "throttle_rate_limit" {
  description = "Sustained request rate (requests per second)"
  type        = number
  default     = 50
}

variable "quota_limit" {
  description = "Maximum number of requests per quota period"
  type        = number
  default     = 10000
}

variable "quota_period" {
  description = "Quota period: DAY, WEEK, or MONTH"
  type        = string
  default     = "DAY"
}

# -----------------------------------------------------------------------------
# Logging & Monitoring
# -----------------------------------------------------------------------------
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "enable_data_trace" {
  description = "Enable full request/response logging (disable in prod for PII protection)"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "FinSight-AI"
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}
