# =============================================================================
# FINSIGHT AI - BEDROCK AGENT OUTPUTS
# =============================================================================

output "agent_id" {
  description = "The ID of the Bedrock Agent"
  value       = aws_bedrockagent_agent.finsight.id
}

output "agent_arn" {
  description = "The ARN of the Bedrock Agent"
  value       = aws_bedrockagent_agent.finsight.agent_arn
}

output "agent_name" {
  description = "The name of the Bedrock Agent"
  value       = aws_bedrockagent_agent.finsight.agent_name
}

output "agent_alias_id" {
  description = "The ID of the production alias"
  value       = aws_bedrockagent_agent_alias.prod.agent_alias_id
}

output "agent_alias_arn" {
  description = "The ARN of the production alias"
  value       = aws_bedrockagent_agent_alias.prod.agent_alias_arn
}

output "calculator_lambda_arn" {
  description = "ARN of the financial calculator Lambda"
  value       = aws_lambda_function.financial_calculator.arn
}

output "calculator_lambda_name" {
  description = "Name of the financial calculator Lambda"
  value       = aws_lambda_function.financial_calculator.function_name
}
