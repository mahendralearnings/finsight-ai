# =============================================================================
# FinSight AI - Glue ETL Module
# =============================================================================

# -----------------------------------------------------------------------------
# IAM Role for Glue
# -----------------------------------------------------------------------------
resource "aws_iam_role" "glue_role" {
  name = "${var.project}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${var.project}-glue-s3-access"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.raw_bucket}",
          "arn:aws:s3:::${var.raw_bucket}/*",
          "arn:aws:s3:::${var.processed_bucket}",
          "arn:aws:s3:::${var.processed_bucket}/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Upload Glue Scripts to S3
# -----------------------------------------------------------------------------
resource "aws_s3_object" "sec_filings_script" {
  bucket = var.raw_bucket
  key    = "glue_scripts/process_sec_filings.py"
  source = "${path.module}/scripts/process_sec_filings.py"
  etag   = filemd5("${path.module}/scripts/process_sec_filings.py")
}

resource "aws_s3_object" "market_data_script" {
  bucket = var.raw_bucket
  key    = "glue_scripts/process_market_data.py"
  source = "${path.module}/scripts/process_market_data.py"
  etag   = filemd5("${path.module}/scripts/process_market_data.py")
}

resource "aws_s3_object" "news_script" {
  bucket = var.raw_bucket
  key    = "glue_scripts/process_news.py"
  source = "${path.module}/scripts/process_news.py"
  etag   = filemd5("${path.module}/scripts/process_news.py")
}

# -----------------------------------------------------------------------------
# Glue Jobs
# -----------------------------------------------------------------------------
locals {
  glue_jobs = {
    process_sec_filings = {
      description = "Process SEC filings (10-K, 10-Q) into chunks for RAG embedding"
      script_key  = aws_s3_object.sec_filings_script.key
    }
    process_market_data = {
      description = "Normalize Yahoo Finance market data with technical indicators"
      script_key  = aws_s3_object.market_data_script.key
    }
    process_news = {
      description = "Process news articles with sentiment analysis for RAG embedding"
      script_key  = aws_s3_object.news_script.key
    }
  }
}

resource "aws_glue_job" "etl_jobs" {
  for_each = local.glue_jobs

  name        = "${var.project}-${each.key}"
  description = each.value.description
  role_arn    = aws_iam_role.glue_role.arn

  glue_version      = "4.0"
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers
  timeout           = var.job_timeout

  command {
    name            = "glueetl"
    script_location = "s3://${var.raw_bucket}/${each.value.script_key}"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"          = "python"
    "--job-bookmark-option"   = "job-bookmark-enable"
    "--enable-metrics"        = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--source_bucket"         = var.raw_bucket
    "--target_bucket"         = var.processed_bucket
    "--account_id"            = var.account_id
    "--TempDir"               = "s3://${var.raw_bucket}/glue_temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups for Glue Jobs
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "glue_logs" {
  for_each = local.glue_jobs

  name              = "/aws-glue/jobs/${var.project}-${each.key}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Scheduled Triggers (Optional - uncomment to enable)
# -----------------------------------------------------------------------------
# resource "aws_glue_trigger" "daily_sec_processing" {
#   name     = "${var.project}-daily-sec-trigger"
#   type     = "SCHEDULED"
#   schedule = "cron(0 2 * * ? *)"  # 2 AM UTC daily
#
#   actions {
#     job_name = aws_glue_job.etl_jobs["process_sec_filings"].name
#   }
#
#   tags = var.tags
# }

# resource "aws_glue_trigger" "daily_market_processing" {
#   name     = "${var.project}-daily-market-trigger"
#   type     = "SCHEDULED"
#   schedule = "cron(0 3 * * ? *)"  # 3 AM UTC daily
#
#   actions {
#     job_name = aws_glue_job.etl_jobs["process_market_data"].name
#   }
#
#   tags = var.tags
# }

# resource "aws_glue_trigger" "daily_news_processing" {
#   name     = "${var.project}-daily-news-trigger"
#   type     = "SCHEDULED"
#   schedule = "cron(0 4 * * ? *)"  # 4 AM UTC daily
#
#   actions {
#     job_name = aws_glue_job.etl_jobs["process_news"].name
#   }
#
#   tags = var.tags
# }
