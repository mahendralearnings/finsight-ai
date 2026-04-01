# =============================================================================
# FINSIGHT AI - GUARDRAILS OUTPUTS
# =============================================================================
# These outputs are used by other modules (like Lambda) to integrate
# with the guardrail.
# =============================================================================

output "guardrail_id" {
  description = "The unique identifier of the guardrail"
  value       = aws_bedrock_guardrail.finsight.guardrail_id
}

output "guardrail_arn" {
  description = "The ARN of the guardrail"
  value       = aws_bedrock_guardrail.finsight.guardrail_arn
}

output "guardrail_version" {
  description = "The version number of the guardrail"
  value       = aws_bedrock_guardrail_version.current.version
}

output "guardrail_name" {
  description = "The name of the guardrail"
  value       = aws_bedrock_guardrail.finsight.name
}

output "guardrail_status" {
  description = "The status of the guardrail"
  value       = aws_bedrock_guardrail.finsight.status
}
