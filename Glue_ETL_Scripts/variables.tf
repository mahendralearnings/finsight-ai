# =============================================================================
# FinSight AI - Glue Module Variables
# =============================================================================

variable "project" {
  description = "Project name"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "raw_bucket" {
  description = "S3 bucket for raw data (source)"
  type        = string
}

variable "processed_bucket" {
  description = "S3 bucket for processed data (target)"
  type        = string
}

# -----------------------------------------------------------------------------
# Glue Job Configuration
# -----------------------------------------------------------------------------
variable "worker_type" {
  description = "Glue worker type (G.1X, G.2X, G.025X)"
  type        = string
  default     = "G.1X"
}

variable "number_of_workers" {
  description = "Number of Glue workers"
  type        = number
  default     = 2
}

variable "job_timeout" {
  description = "Job timeout in minutes"
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Project   = "FinSight-AI"
    Component = "Glue-ETL"
    ManagedBy = "Terraform"
  }
}
