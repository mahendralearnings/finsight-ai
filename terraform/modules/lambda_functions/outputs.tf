output "lambda_function_arns" {
  description = "ARNs of all Lambda functions"
  value = {
    for k, v in aws_lambda_function.finsight : k => v.arn
  }
}

output "lambda_function_names" {
  description = "Names of all Lambda functions"
  value = {
    for k, v in aws_lambda_function.finsight : k => v.function_name
  }
}

output "rag_query_handler_arn" {
  description = "ARN of the RAG query handler Lambda (used by API Gateway)"
  value       = aws_lambda_function.finsight["rag_query_handler"].arn
}

output "rag_query_handler_invoke_arn" {
  description = "Invoke ARN for API Gateway integration"
  value       = aws_lambda_function.finsight["rag_query_handler"].invoke_arn
}

output "embed_documents_arn" {
  description = "ARN of the embed_documents Lambda (used by S3 trigger)"
  value       = aws_lambda_function.finsight["embed_documents"].arn
}

output "log_group_names" {
  description = "CloudWatch log group names"
  value = {
    for k, v in aws_cloudwatch_log_group.lambda_logs : k => v.name
  }
}


output "rag_query_handler_function_name" {
  description = "Function name for rag_query_handler Lambda"
  value       = aws_lambda_function.finsight["rag_query_handler"].function_name

}

