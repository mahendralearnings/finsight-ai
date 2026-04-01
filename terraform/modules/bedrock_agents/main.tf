# =============================================================================
# FINSIGHT AI - BEDROCK AGENT
# =============================================================================
# This module creates a Bedrock Agent for autonomous financial analysis.
# The agent can:
#   - Search SEC filings (via RAG)
#   - Perform financial calculations
#   - Reason about multi-step tasks
#
# Author: Mahendra Nali
# =============================================================================

# -----------------------------------------------------------------------------
# IAM ROLE FOR BEDROCK AGENT
# -----------------------------------------------------------------------------
resource "aws_iam_role" "agent_role" {
  name = "${var.project_name}-bedrock-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = var.tags
}

# Policy for Agent to invoke foundation model
# Policy for Agent to invoke foundation model
resource "aws_iam_role_policy" "agent_bedrock_policy" {
  name = "${var.project_name}-agent-bedrock-policy"
  role = aws_iam_role.agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:GetFoundationModel",
          "bedrock:GetInferenceProfile",
          "bedrock:InvokeAgent",
          "bedrock:GetAgentMemory",
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ApplyGuardrail"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:guardrail/*"
      }
    ]
  })
}

# Policy for Agent to invoke Lambda (Action Groups)
resource "aws_iam_role_policy" "agent_lambda_policy" {
  name = "${var.project_name}-agent-lambda-policy"
  role = aws_iam_role.agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = aws_lambda_function.financial_calculator.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# LAMBDA FUNCTION FOR FINANCIAL CALCULATOR (Action Group)
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}

# IAM Role for Lambda
resource "aws_iam_role" "calculator_lambda_role" {
  name = "${var.project_name}-calculator-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "calculator_lambda_basic" {
  role       = aws_iam_role.calculator_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Package Lambda code
data "archive_file" "calculator_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/financial_calculator/handler.py"
  output_path = "${path.module}/lambda/financial_calculator.zip"
}

# Lambda Function
resource "aws_lambda_function" "financial_calculator" {
  filename         = data.archive_file.calculator_lambda_zip.output_path
  function_name    = "${var.project_name}-financial-calculator"
  role             = aws_iam_role.calculator_lambda_role.arn
  handler          = "handler.handler"
  source_code_hash = data.archive_file.calculator_lambda_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  tags = var.tags
}

# Permission for Bedrock to invoke Lambda
resource "aws_lambda_permission" "bedrock_invoke" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.financial_calculator.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
}

# -----------------------------------------------------------------------------
# BEDROCK AGENT
# -----------------------------------------------------------------------------
resource "aws_bedrockagent_agent" "finsight" {
  agent_name              = "${var.project_name}-agent"
  agent_resource_role_arn = aws_iam_role.agent_role.arn
  description             = "FinSight AI Agent for autonomous financial analysis"
  
  # Foundation Model - Using Haiku for cost efficiency
  foundation_model = "anthropic.claude-3-haiku-20240307-v1:0"
  
  # Idle timeout (seconds)
  idle_session_ttl_in_seconds = 600

  # Agent Instructions (System Prompt)
  instruction = <<-EOT
    You are FinSight AI, an intelligent financial analysis assistant.
    
    YOUR CAPABILITIES:
    1. Search and analyze SEC filings (10-K, 10-Q reports)
    2. Perform financial calculations (growth rates, ratios, margins, CAGR)
    3. Compare companies and metrics
    4. Provide data-driven insights
    
    RULES:
    - Always use the financial calculator for mathematical operations
    - Cite sources when referencing filing data
    - Express uncertainty when data is incomplete
    - NEVER provide investment advice or stock recommendations
    - NEVER predict stock prices
    - Be precise with numbers and calculations
    
    CALCULATION TOOLS AVAILABLE:
    - calculate_growth_rate: For YoY or period comparisons
    - calculate_ratio: For P/E, D/E, and other ratios
    - calculate_margin: For profit margin analysis
    - calculate_cagr: For multi-year growth analysis
    - compare_values: For ranking and comparing companies
    
    When asked to compare or calculate, ALWAYS use the appropriate tool.
    Do not perform calculations in your head - use the calculator tools.
  EOT

  # Attach Guardrails (from Feature 1!)
  guardrail_configuration {
    guardrail_identifier = var.guardrail_id
    guardrail_version    = var.guardrail_version
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# ACTION GROUP - Financial Calculator
# -----------------------------------------------------------------------------
resource "aws_bedrockagent_agent_action_group" "financial_calculator" {
  agent_id          = aws_bedrockagent_agent.finsight.id
  agent_version     = "DRAFT"
  action_group_name = "financial-calculator"
  description       = "Financial calculation tools for growth rates, ratios, margins, and comparisons"

  action_group_executor {
    lambda = aws_lambda_function.financial_calculator.arn
  }

  api_schema {
    payload = file("${path.module}/openapi/financial_tools.yaml")
  }
}

# -----------------------------------------------------------------------------
# PREPARE AGENT (makes it ready for use)
# -----------------------------------------------------------------------------
resource "null_resource" "prepare_agent" {
  depends_on = [
    aws_bedrockagent_agent.finsight,
    aws_bedrockagent_agent_action_group.financial_calculator
  ]

  provisioner "local-exec" {
    command = "aws bedrock-agent prepare-agent --agent-id ${aws_bedrockagent_agent.finsight.id} --region ${var.aws_region}"
  }

  triggers = {
    agent_id     = aws_bedrockagent_agent.finsight.id
    action_group = aws_bedrockagent_agent_action_group.financial_calculator.action_group_name
  }
}

# Create an alias for the agent (for invoking)
# Wait for agent to finish preparing
resource "time_sleep" "wait_for_agent_preparation" {
  depends_on = [null_resource.prepare_agent]
  
  create_duration = "30s"
}

# Create an alias for the agent (for invoking)
resource "aws_bedrockagent_agent_alias" "prod" {
  agent_id         = aws_bedrockagent_agent.finsight.id
  agent_alias_name = "prod"
  description      = "Production alias for FinSight AI Agent"

  depends_on = [time_sleep.wait_for_agent_preparation]

  tags = var.tags
}