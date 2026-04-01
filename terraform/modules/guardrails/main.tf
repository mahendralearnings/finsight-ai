# =============================================================================
# FINSIGHT AI - BEDROCK GUARDRAILS
# =============================================================================
# This module creates a Bedrock Guardrail for AI safety in our financial
# analysis platform.
#
# Author: Mahendra Nali
# =============================================================================

resource "aws_bedrock_guardrail" "finsight" {
  name        = "${var.project_name}-safety-guardrail"
  description = "Safety guardrail for FinSight AI financial analysis platform"

  blocked_input_messaging  = "I cannot process this request. Please rephrase your question about financial analysis."
  blocked_outputs_messaging = "I cannot provide this response. Please try a different question."

  # ---------------------------------------------------------------------------
  # CONTENT FILTERS
  # ---------------------------------------------------------------------------
  content_policy_config {
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }

    filters_config {
      type            = "INSULTS"
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
    }

    filters_config {
      type            = "SEXUAL"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }

    filters_config {
      type            = "VIOLENCE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }

    filters_config {
      type            = "MISCONDUCT"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }

    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }

  # ---------------------------------------------------------------------------
  # DENIED TOPICS (reduced examples to meet AWS quota - max 5 total)
  # ---------------------------------------------------------------------------
  topic_policy_config {
    topics_config {
      name       = "investment_advice"
      type       = "DENY"
      definition = "Recommendations to buy, sell, or hold stocks, bonds, crypto. Includes price predictions and portfolio advice."

      examples = [
        "Should I buy Apple stock?",
        "Is Tesla a good investment?",
        "What will Amazon stock price be next month?"
      ]
    }

    topics_config {
      name       = "political_opinions"
      type       = "DENY"
      definition = "Opinions about political parties, candidates, elections, or government policies."

      examples = [
        "Which party is better for the stock market?"
      ]
    }

    topics_config {
      name       = "illegal_financial"
      type       = "DENY"
      definition = "Info about insider trading, market manipulation, money laundering, or tax evasion."

      examples = [
        "How do I trade on insider information?"
      ]
    }
  }

  # ---------------------------------------------------------------------------
  # SENSITIVE INFORMATION (PII) FILTERS
  # ---------------------------------------------------------------------------
  sensitive_information_policy_config {
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }

    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }

    pii_entities_config {
      type   = "US_SOCIAL_SECURITY_NUMBER"
      action = "BLOCK"
    }

    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "BLOCK"
    }

    pii_entities_config {
      type   = "US_BANK_ACCOUNT_NUMBER"
      action = "BLOCK"
    }

    pii_entities_config {
      type   = "DRIVER_ID"
      action = "BLOCK"
    }

    pii_entities_config {
      type   = "US_PASSPORT_NUMBER"
      action = "BLOCK"
    }

    pii_entities_config {
      type   = "AWS_ACCESS_KEY"
      action = "BLOCK"
    }

    pii_entities_config {
      type   = "AWS_SECRET_KEY"
      action = "BLOCK"
    }

    pii_entities_config {
      type   = "PASSWORD"
      action = "BLOCK"
    }

    # Custom regex for Aadhaar numbers
    regexes_config {
      name        = "aadhaar_number"
      description = "Indian Aadhaar ID numbers"
      pattern     = "[0-9]{4}\\s?[0-9]{4}\\s?[0-9]{4}"
      action      = "BLOCK"
    }
  }

  # ---------------------------------------------------------------------------
  # WORD FILTERS
  # ---------------------------------------------------------------------------
  word_policy_config {
    words_config {
      text = "insider trading"
    }
    words_config {
      text = "pump and dump"
    }
    words_config {
      text = "guaranteed returns"
    }
    words_config {
      text = "get rich quick"
    }

    managed_word_lists_config {
      type = "PROFANITY"
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Component   = "ai-safety"
    ManagedBy   = "terraform"
  }
}

resource "aws_bedrock_guardrail_version" "current" {
  guardrail_arn = aws_bedrock_guardrail.finsight.guardrail_arn
  description   = "Production version"
}
