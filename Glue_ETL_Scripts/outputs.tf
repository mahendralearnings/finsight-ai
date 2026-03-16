# =============================================================================
# FinSight AI - Glue Module Outputs
# =============================================================================

output "glue_role_arn" {
  description = "ARN of the Glue IAM role"
  value       = aws_iam_role.glue_role.arn
}

output "glue_role_name" {
  description = "Name of the Glue IAM role"
  value       = aws_iam_role.glue_role.name
}

output "job_names" {
  description = "Names of all Glue ETL jobs"
  value = {
    for k, v in aws_glue_job.etl_jobs : k => v.name
  }
}

output "job_arns" {
  description = "ARNs of all Glue ETL jobs"
  value = {
    for k, v in aws_glue_job.etl_jobs : k => v.arn
  }
}

output "script_locations" {
  description = "S3 locations of Glue scripts"
  value = {
    sec_filings = "s3://${var.raw_bucket}/${aws_s3_object.sec_filings_script.key}"
    market_data = "s3://${var.raw_bucket}/${aws_s3_object.market_data_script.key}"
    news        = "s3://${var.raw_bucket}/${aws_s3_object.news_script.key}"
  }
}

# -----------------------------------------------------------------------------
# CLI Commands for Running Jobs
# -----------------------------------------------------------------------------
output "run_commands" {
  description = "AWS CLI commands to run each job"
  value = {
    for k, v in aws_glue_job.etl_jobs : k => "aws glue start-job-run --job-name ${v.name}"
  }
}
