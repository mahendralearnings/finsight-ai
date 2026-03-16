variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "prod"
}

variable "project" {
  default = "finsight-ai"
}

variable "db_password" {
  description = "RDS pgvector master password"
  sensitive   = true
  default     = "FinSight@2024!"
}

variable "redshift_password" {
  description = "Redshift admin password"
  sensitive   = true
  default     = "FinSight@2024!"
}