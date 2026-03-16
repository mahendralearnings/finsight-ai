# =============================================================================
# FinSight AI - Root Outputs
# =============================================================================

# API Gateway
output "api_endpoint" {
  description = "FinSight AI API endpoint"
  value       = module.api_gateway.api_endpoint
}

output "api_query_endpoint" {
  description = "RAG Query endpoint URL"
  value       = module.api_gateway.query_endpoint
}

output "api_key_value" {
  description = "API Key for authentication"
  value       = module.api_gateway.api_key_value
  sensitive   = true
}

# Lambda (optional - useful for debugging)
output "lambda_function_arns" {
  description = "Lambda function ARNs"
  value       = module.lambda_functions.lambda_function_arns
}

# S3 (optional)
output "s3_bucket_names" {
  description = "S3 bucket names"
  value       = module.s3.bucket_names
}