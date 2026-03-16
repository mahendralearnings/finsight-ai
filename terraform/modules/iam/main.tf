# ──────────────────────────────────────────────
# FinSight AI — IAM Roles (Least Privilege)
# Each service gets ONLY what it needs
# ──────────────────────────────────────────────

# ─── 1. LAMBDA EXECUTION ROLE ─────────────────
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Allow Lambda to run inside VPC
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Custom policy: S3 + Bedrock + Secrets Manager
resource "aws_iam_role_policy" "lambda_custom" {
  name = "${var.project}-lambda-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::${var.project}-raw-${var.account_id}/*",
          "arn:aws:s3:::${var.project}-processed-${var.account_id}/*",
          "arn:aws:s3:::${var.project}-embeddings-${var.account_id}/*",
          "arn:aws:s3:::${var.project}-raw-${var.account_id}",
          "arn:aws:s3:::${var.project}-processed-${var.account_id}",
          "arn:aws:s3:::${var.project}-embeddings-${var.account_id}"
        ]
      },
      {
        Sid    = "BedrockAccess"
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0",
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
        ]
      },
      {
        Sid    = "SecretsAccess"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:us-east-1:${var.account_id}:secret:finsight/*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# ─── 2. GLUE SERVICE ROLE ─────────────────────
resource "aws_iam_role" "glue_service" {
  name = "${var.project}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3" {
  name = "${var.project}-glue-s3-policy"
  role = aws_iam_role.glue_service.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
      Resource = [
        "arn:aws:s3:::${var.project}-raw-${var.account_id}/*",
        "arn:aws:s3:::${var.project}-processed-${var.account_id}/*"
      ]
    }]
  })
}

# ─── 3. REDSHIFT ROLE ────────────────────────
resource "aws_iam_role" "redshift" {
  name = "${var.project}-redshift-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "redshift.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "redshift_s3" {
  name = "${var.project}-redshift-s3-policy"
  role = aws_iam_role.redshift.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        "arn:aws:s3:::${var.project}-processed-${var.account_id}",
        "arn:aws:s3:::${var.project}-processed-${var.account_id}/*"
      ]
    }]
  })
}


resource "aws_iam_role_policy" "lambda_marketplace" {
  name = "bedrock-marketplace-access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aws-marketplace:ViewSubscriptions",
          "aws-marketplace:Subscribe",
          "aws-marketplace:Unsubscribe"
        ]
        Resource = "*"
      }
    ]
  })
}