# ===============================
# FinSight AI - Terraform Variables Example
# ===============================
# Copy this file to terraform.tfvars and fill in your values
# NEVER commit terraform.tfvars to git!

# AWS Configuration
aws_region = "us-east-1"
account_id = "YOUR_AWS_ACCOUNT_ID"

# Project Configuration
project     = "finsight"
environment = "dev"

# RDS Configuration
db_instance_class = "db.t3.micro"
db_name           = "finsight"
db_username       = "finsight_admin"
# db_password is stored in Secrets Manager, not here

# Lambda Configuration
lambda_memory_size = 256
lambda_timeout     = 60

# API Gateway Configuration
api_throttle_burst_limit = 100
api_throttle_rate_limit  = 50
api_quota_limit          = 10000

# Bedrock Models
embedding_model_id = "amazon.titan-embed-text-v2:0"
llm_model_id       = "anthropic.claude-3-haiku-20240307-v1:0"

# Tags
tags = {
  Project     = "FinSight AI"
  Environment = "Development"
  Owner       = "Your Name"
  CostCenter  = "AI-ML"
}
