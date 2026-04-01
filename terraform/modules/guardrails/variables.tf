# =============================================================================
# FINSIGHT AI - GUARDRAILS VARIABLES
# =============================================================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "finsight-ai"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "content_filter_strength" {
  description = "Default strength for content filters (LOW, MEDIUM, HIGH)"
  type        = string
  default     = "HIGH"

  validation {
    condition     = contains(["LOW", "MEDIUM", "HIGH"], var.content_filter_strength)
    error_message = "Content filter strength must be LOW, MEDIUM, or HIGH."
  }
}
