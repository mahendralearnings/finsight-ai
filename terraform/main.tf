module "s3" {
  source     = "./modules/s3_data_lake"
  project    = var.project
  account_id = data.aws_caller_identity.current.account_id
}


###For IAM module 

module "iam" {
  source     = "./modules/iam"
  project    = var.project
  account_id = data.aws_caller_identity.current.account_id
}


#For secret manager

module "secrets" {
  source  = "./modules/secrets"
  project = var.project
}


module "networking" {
  source  = "./modules/networking"
  project = var.project
}


###For RDS_pgvector

module "rds" {
  source             = "./modules/rds_pgvector"
  project            = var.project
  private_subnet_ids = module.networking.private_subnet_ids
  rds_sg_id          = module.networking.rds_sg_id
  db_password        = var.db_password
}

module "lambda_functions" {
  source                   = "./modules/lambda_functions"
  aws_region               = "us-east-1"
  lambda_exec_role_arn     = "arn:aws:iam::617297630012:role/finsight-ai-lambda-exec-role"
  private_subnet_ids       = module.networking.private_subnet_ids
  lambda_security_group_id = module.networking.lambda_sg_id
  rds_secret_id            = "finsight/rds/credentials"
  s3_raw_bucket            = module.s3.bucket_names["raw"]
  s3_processed_bucket      = module.s3.bucket_names["processed"]
}


module "api_gateway" {
  source = "./modules/api_gateway"

  project_name = var.project   # Changed from var.project_name

  rag_query_handler_invoke_arn    = module.lambda_functions.rag_query_handler_invoke_arn
  rag_query_handler_function_name = module.lambda_functions.rag_query_handler_function_name

  throttle_burst_limit = 100
  throttle_rate_limit  = 50
  quota_limit          = 10000
  quota_period         = "DAY"

  log_retention_days = 30
  enable_data_trace  = true

  tags = {
    Project     = var.project
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}


# =============================================================================
# GUARDRAILS MODULE
# =============================================================================

module "guardrails" {
  source = "./modules/guardrails"
  
  project_name = "finsight-ai"
  environment  = "dev"
}
# Output the guardrail ID for use in Lambda
output "guardrail_id" {
  description = "Guardrail ID for Lambda integration"
  value       = module.guardrails.guardrail_id
}

output "guardrail_version" {
  description = "Guardrail version for Lambda integration"
  value       = module.guardrails.guardrail_version
}

# =============================================================================
# ADD THIS TO YOUR ROOT terraform/main.tf
# =============================================================================

# Bedrock Agent Module
module "bedrock_agent" {
  source = "./modules/bedrock_agents"
  
  project_name = "finsight-ai"
  aws_region   = "us-east-1"
  environment  = "dev"
  
  # Connect to Guardrails (Feature 1!)
  guardrail_id      = module.guardrails.guardrail_id
  guardrail_version = module.guardrails.guardrail_version
  
  tags = {
    Project     = "finsight-ai"
    Component   = "bedrock-agent"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

# =============================================================================
# OUTPUTS (Add these to your root main.tf as well)
# =============================================================================

output "agent_id" {
  description = "Bedrock Agent ID"
  value       = module.bedrock_agent.agent_id
}

output "agent_alias_id" {
  description = "Bedrock Agent Alias ID (for invoking)"
  value       = module.bedrock_agent.agent_alias_id
}

output "calculator_lambda_name" {
  description = "Financial Calculator Lambda name"
  value       = module.bedrock_agent.calculator_lambda_name
}
