locals {
  functions = {
    ingest_sec = {
      handler     = "handler.lambda_handler"
      timeout     = 300
      memory      = 512
      needs_vpc   = false          # internet only, no RDS
      description = "Ingests SEC EDGAR filings into S3 raw bucket"
      source_dir  = "${path.module}/../../../lambda/ingest_sec"
      environment = {
        S3_RAW_BUCKET = var.s3_raw_bucket
        SECRET_ID     = var.sec_edgar_secret_id
        REGION        = var.aws_region
      }
    }
    ingest_market = {
      handler     = "handler.lambda_handler"
      timeout     = 180
      memory      = 256
      needs_vpc   = false          # internet only, no RDS
      description = "Ingests market data from Yahoo Finance into S3"
      source_dir  = "${path.module}/../../../lambda/ingest_market"
      environment = {
        S3_RAW_BUCKET = var.s3_raw_bucket
        SECRET_ID     = var.yahoo_finance_secret_id
        REGION        = var.aws_region
      }
    }
    embed_documents = {
      handler     = "handler.lambda_handler"
      timeout     = 600
      memory      = 1024
      needs_vpc   = true           # needs RDS access
      description = "Generates Bedrock embeddings and stores in pgvector"
      source_dir  = "${path.module}/../../../lambda/embed_documents"
      environment = {
        S3_PROCESSED_BUCKET = var.s3_processed_bucket
        DB_SECRET_ID        = var.rds_secret_id
        BEDROCK_REGION      = var.aws_region
        EMBEDDING_MODEL     = var.embedding_model
      }
    }
    rag_query_handler = {
      handler     = "handler.lambda_handler"
      timeout     = 30
      memory      = 512
      needs_vpc   = true           # needs RDS access
      description = "RAG query handler - pgvector similarity search + Bedrock LLM"
      source_dir  = "${path.module}/../../../lambda/rag_query_handler"
      environment = {
        DB_SECRET_ID   = var.rds_secret_id
        BEDROCK_REGION = var.aws_region
        LLM_MODEL      = var.llm_model
        TOP_K          = "5"
      }
    }
  }

  # EventBridge schedules for ingest functions only
  scheduled_functions = {
    ingest_sec    = "rate(6 hours)"
    ingest_market = "rate(1 hour)"
  }
}

# ─── ZIP each Lambda source directory ───────────────────────────────────────
data "archive_file" "lambda_zips" {
  for_each    = local.functions
  type        = "zip"
  source_dir  = each.value.source_dir
  output_path = "${path.module}/dist/${each.key}.zip"
}

# ─── Lambda Functions ────────────────────────────────────────────────────────
resource "aws_lambda_function" "finsight" {
  for_each = local.functions

  function_name    = "finsight-${each.key}"
  filename         = data.archive_file.lambda_zips[each.key].output_path
  source_code_hash = data.archive_file.lambda_zips[each.key].output_base64sha256
  role             = var.lambda_exec_role_arn
  handler          = each.value.handler
  runtime          = "python3.12"
  timeout          = each.value.timeout
  memory_size      = each.value.memory
  description      = each.value.description
  layers           = each.value.needs_vpc ? [var.psycopg2_layer_arn] : []


  # Only attach VPC for functions that need RDS access
  dynamic "vpc_config" {
    for_each = each.value.needs_vpc ? [1] : []
    content {
      subnet_ids         = var.private_subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  environment {
    variables = each.value.environment
  }

  tags = var.tags

  depends_on = [data.archive_file.lambda_zips]
}

# ─── CloudWatch Log Groups ───────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = local.functions

  name              = "/aws/lambda/finsight-${each.key}"
  retention_in_days = 14
  tags              = var.tags
}

# ─── EventBridge Schedules (ingest functions only) ──────────────────────────
resource "aws_cloudwatch_event_rule" "ingest_schedule" {
  for_each = local.scheduled_functions

  name                = "finsight-${each.key}-schedule"
  description         = "Schedule for finsight-${each.key}"
  schedule_expression = each.value
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "lambda_targets" {
  for_each = local.scheduled_functions

  rule      = aws_cloudwatch_event_rule.ingest_schedule[each.key].name
  target_id = "finsight-${each.key}"
  arn       = aws_lambda_function.finsight[each.key].arn
}

resource "aws_lambda_permission" "eventbridge" {
  for_each = local.scheduled_functions

  statement_id  = "AllowEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finsight[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingest_schedule[each.key].arn
}

# ─── Allow embed_documents to be triggered by S3 ────────────────────────────
resource "aws_lambda_permission" "s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finsight["embed_documents"].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.s3_processed_bucket}"
}
