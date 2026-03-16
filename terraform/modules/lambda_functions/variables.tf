variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
  default     = "617297630012"
}

variable "lambda_exec_role_arn" {
  description = "IAM role ARN for Lambda execution"
  type        = string
  default     = "arn:aws:iam::617297630012:role/finsight-ai-lambda-exec-role"
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Lambda VPC config"
  type        = list(string)
  default     = ["subnet-00106e399c7619201", "subnet-05370a9b1b549888b"]
}

variable "lambda_security_group_id" {
  description = "Security group ID for Lambda functions"
  type        = string
  default     = "sg-0ebc632d5a95b14c4"
}

variable "rds_secret_id" {
  description = "Secrets Manager secret ID for RDS credentials"
  type        = string
  default     = "finsight/rds/credentials"
}

variable "sec_edgar_secret_id" {
  description = "Secrets Manager secret ID for SEC EDGAR API"
  type        = string
  default     = "finsight/sec-edgar"
}

variable "newsapi_secret_id" {
  description = "Secrets Manager secret ID for NewsAPI"
  type        = string
  default     = "finsight/newsapi"
}

variable "yahoo_finance_secret_id" {
  description = "Secrets Manager secret ID for Yahoo Finance"
  type        = string
  default     = "finsight/yahoo-finance"
}

variable "s3_raw_bucket" {
  description = "S3 raw data bucket name"
  type        = string
  default     = "finsight-ai-raw-617297630012"
}

variable "s3_processed_bucket" {
  description = "S3 processed data bucket name"
  type        = string
  default     = "finsight-ai-processed-617297630012"
}

variable "s3_embeddings_bucket" {
  description = "S3 embeddings bucket name"
  type        = string
  default     = "finsight-ai-embeddings-617297630012"
}

variable "embedding_model" {
  description = "Bedrock embedding model ID"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "llm_model" {
  description = "Bedrock LLM model ID"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default = {
    Project    = "finsight-ai"
    ManagedBy  = "terraform"
    Env        = "dev"
  }
}


variable "psycopg2_layer_arn" {
  description = "psycopg2 Lambda layer ARN"
  type        = string
  default     = "arn:aws:lambda:us-east-1:617297630012:layer:finsight-psycopg2:1"
}
