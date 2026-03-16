output "lambda_exec_role_arn" {
  value = aws_iam_role.lambda_exec.arn
}

output "glue_role_arn" {
  value = aws_iam_role.glue_service.arn
}

output "redshift_role_arn" {
  value = aws_iam_role.redshift.arn
}