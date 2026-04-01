# =============================================================================
# FINSIGHT AI - BEDROCK AGENT VARIABLES
# =============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "finsight-ai"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Guardrails integration (from Feature 1)
variable "guardrail_id" {
  description = "Bedrock Guardrail ID to attach to the agent"
  type        = string
}

variable "guardrail_version" {
  description = "Bedrock Guardrail version"
  type        = string
  default     = "DRAFT"
}

variable "tags" {
  description = "Tags for all resources"
  type        = map(string)
  default = {
    Project   = "finsight-ai"
    Component = "bedrock-agent"
    ManagedBy = "terraform"
  }
}
