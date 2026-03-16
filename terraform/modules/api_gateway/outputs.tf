# =============================================================================
# FinSight AI - API Gateway Module Outputs
# =============================================================================

output "api_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.finsight_api.id
}

output "api_endpoint" {
  description = "Base URL for the API Gateway stage"
  value       = aws_api_gateway_stage.prod.invoke_url
}

output "query_endpoint" {
  description = "Full URL for the /query endpoint"
  value       = "${aws_api_gateway_stage.prod.invoke_url}/query"
}

output "api_key_id" {
  description = "API Key ID"
  value       = aws_api_gateway_api_key.finsight_key.id
}

output "api_key_value" {
  description = "API Key value (sensitive - use for testing)"
  value       = aws_api_gateway_api_key.finsight_key.value
  sensitive   = true
}

output "usage_plan_id" {
  description = "Usage Plan ID"
  value       = aws_api_gateway_usage_plan.finsight.id
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group for API Gateway access logs"
  value       = aws_cloudwatch_log_group.api_gateway.name
}

output "stage_name" {
  description = "Deployed stage name"
  value       = aws_api_gateway_stage.prod.stage_name
}

# -----------------------------------------------------------------------------
# Convenience Outputs for Testing
# -----------------------------------------------------------------------------
output "curl_test_command" {
  description = "Sample curl command to test the API (replace API_KEY)"
  value       = <<-EOT
    curl -X POST '${aws_api_gateway_stage.prod.invoke_url}/query' \
      -H 'Content-Type: application/json' \
      -H 'x-api-key: <YOUR_API_KEY>' \
      -d '{"question": "What were Apple revenue drivers in Q3?"}'
  EOT
}
