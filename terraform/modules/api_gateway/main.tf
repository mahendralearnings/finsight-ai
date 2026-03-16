# =============================================================================
# FinSight AI - API Gateway Module
# Production-ready REST API for RAG Query Endpoint
# =============================================================================

# -----------------------------------------------------------------------------
# REST API Definition
# -----------------------------------------------------------------------------
resource "aws_api_gateway_rest_api" "finsight_api" {
  name        = "${var.project_name}-api"
  description = "FinSight AI RAG Query API - Financial Intelligence Platform"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# /query Resource
# -----------------------------------------------------------------------------
resource "aws_api_gateway_resource" "query" {
  rest_api_id = aws_api_gateway_rest_api.finsight_api.id
  parent_id   = aws_api_gateway_rest_api.finsight_api.root_resource_id
  path_part   = "query"
}

# -----------------------------------------------------------------------------
# POST /query Method (with API Key required)
# -----------------------------------------------------------------------------
resource "aws_api_gateway_method" "query_post" {
  rest_api_id      = aws_api_gateway_rest_api.finsight_api.id
  resource_id      = aws_api_gateway_resource.query.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

# -----------------------------------------------------------------------------
# Lambda Proxy Integration
# -----------------------------------------------------------------------------
resource "aws_api_gateway_integration" "query_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.finsight_api.id
  resource_id             = aws_api_gateway_resource.query.id
  http_method             = aws_api_gateway_method.query_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.rag_query_handler_invoke_arn
}

# -----------------------------------------------------------------------------
# Lambda Permission for API Gateway
# -----------------------------------------------------------------------------
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.rag_query_handler_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.finsight_api.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# CORS - OPTIONS Method for Preflight Requests
# -----------------------------------------------------------------------------
resource "aws_api_gateway_method" "query_options" {
  rest_api_id   = aws_api_gateway_rest_api.finsight_api.id
  resource_id   = aws_api_gateway_resource.query.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "query_options" {
  rest_api_id = aws_api_gateway_rest_api.finsight_api.id
  resource_id = aws_api_gateway_resource.query.id
  http_method = aws_api_gateway_method.query_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "query_options_200" {
  rest_api_id = aws_api_gateway_rest_api.finsight_api.id
  resource_id = aws_api_gateway_resource.query.id
  http_method = aws_api_gateway_method.query_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "query_options" {
  rest_api_id = aws_api_gateway_rest_api.finsight_api.id
  resource_id = aws_api_gateway_resource.query.id
  http_method = aws_api_gateway_method.query_options.http_method
  status_code = aws_api_gateway_method_response.query_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Api-Key,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.query_options]
}

# -----------------------------------------------------------------------------
# Deployment & Stage
# -----------------------------------------------------------------------------
resource "aws_api_gateway_deployment" "finsight" {
  rest_api_id = aws_api_gateway_rest_api.finsight_api.id

  # Redeploy when any of these change
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.query.id,
      aws_api_gateway_method.query_post.id,
      aws_api_gateway_integration.query_lambda.id,
      aws_api_gateway_method.query_options.id,
      aws_api_gateway_integration.query_options.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.query_lambda,
    aws_api_gateway_integration.query_options,
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.finsight.id
  rest_api_id   = aws_api_gateway_rest_api.finsight_api.id
  stage_name    = var.stage_name

  # Enable CloudWatch logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId         = "$context.requestId"
      ip                = "$context.identity.sourceIp"
      caller            = "$context.identity.caller"
      user              = "$context.identity.user"
      requestTime       = "$context.requestTime"
      httpMethod        = "$context.httpMethod"
      resourcePath      = "$context.resourcePath"
      status            = "$context.status"
      protocol          = "$context.protocol"
      responseLength    = "$context.responseLength"
      integrationError  = "$context.integrationErrorMessage"
      integrationLatency = "$context.integrationLatency"
      responseLatency   = "$context.responseLatency"
    })
  }
  
  depends_on = [aws_api_gateway_account.main]

  tags = var.tags
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group for API Gateway
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/api-gateway/${var.project_name}-api"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# API Gateway Account Settings (for CloudWatch logging)
# -----------------------------------------------------------------------------
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch.arn
}

resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${var.project_name}-api-gateway-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# -----------------------------------------------------------------------------
# API Key
# -----------------------------------------------------------------------------
resource "aws_api_gateway_api_key" "finsight_key" {
  name        = "${var.project_name}-api-key"
  description = "API Key for FinSight AI RAG Query API"
  enabled     = true

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Usage Plan with Rate Limiting
# -----------------------------------------------------------------------------
resource "aws_api_gateway_usage_plan" "finsight" {
  name        = "${var.project_name}-usage-plan"
  description = "Usage plan with rate limiting for FinSight AI API"

  api_stages {
    api_id = aws_api_gateway_rest_api.finsight_api.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }

  # Throttling: Burst limit + sustained rate
  throttle_settings {
    burst_limit = var.throttle_burst_limit  # Max concurrent requests
    rate_limit  = var.throttle_rate_limit   # Requests per second
  }

  # Quota: Total requests per period
  quota_settings {
    limit  = var.quota_limit    # Total requests
    period = var.quota_period   # DAY, WEEK, or MONTH
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Link API Key to Usage Plan
# -----------------------------------------------------------------------------
resource "aws_api_gateway_usage_plan_key" "finsight" {
  key_id        = aws_api_gateway_api_key.finsight_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.finsight.id
}

# -----------------------------------------------------------------------------
# Method Settings (detailed logging + throttling at method level)
# -----------------------------------------------------------------------------
resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.finsight_api.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = "*/*"

  settings {
    logging_level          = "INFO"
    data_trace_enabled     = var.enable_data_trace  # Log full request/response (disable in prod for PII)
    metrics_enabled        = true
    throttling_burst_limit = var.throttle_burst_limit
    throttling_rate_limit  = var.throttle_rate_limit
  }
}



