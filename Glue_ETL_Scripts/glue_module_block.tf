# =============================================================================
# FinSight AI - Glue ETL Module (Add to your root main.tf)
# =============================================================================

module "glue" {
  source = "./modules/glue"

  project          = var.project
  account_id       = data.aws_caller_identity.current.account_id
  raw_bucket       = module.s3.bucket_names["raw"]
  processed_bucket = module.s3.bucket_names["processed"]

  # Job configuration
  worker_type       = "G.1X"    # Cost-effective for small data
  number_of_workers = 2         # Minimum for Glue 4.0
  job_timeout       = 30        # Minutes

  tags = {
    Project   = var.project
    Component = "Glue-ETL"
    ManagedBy = "Terraform"
  }
}

# -----------------------------------------------------------------------------
# Add to your root outputs.tf
# -----------------------------------------------------------------------------
output "glue_job_names" {
  description = "Glue ETL job names"
  value       = module.glue.job_names
}

output "glue_run_commands" {
  description = "CLI commands to run Glue jobs"
  value       = module.glue.run_commands
}
