#!/bin/bash
# FinSight AI - CloudWatch Alarms Setup

ACCOUNT_ID="617297630012"
SNS_TOPIC="arn:aws:sns:us-east-1:${ACCOUNT_ID}:finsight-ai-alerts"

echo "Creating CloudWatch Alarms..."

# =============================================================================
# ALARM 1: Lambda Errors - ingest_sec
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-lambda-ingest_sec-errors" \
  --alarm-description "Alert when ingest_sec Lambda has errors" \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=finsight-ingest_sec \
  --statistic Sum \
  --period 300 \
  --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: Lambda ingest_sec errors"

# =============================================================================
# ALARM 2: Lambda Errors - embed_documents
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-lambda-embed_documents-errors" \
  --alarm-description "Alert when embed_documents Lambda has errors" \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=finsight-embed_documents \
  --statistic Sum \
  --period 300 \
  --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: Lambda embed_documents errors"

# =============================================================================
# ALARM 3: Lambda Errors - rag_query_handler
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-lambda-rag_query-errors" \
  --alarm-description "Alert when RAG query Lambda has errors" \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=finsight-rag_query_handler \
  --statistic Sum \
  --period 300 \
  --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: Lambda rag_query errors"

# =============================================================================
# ALARM 4: Lambda Duration - rag_query (slow = bad UX)
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-lambda-rag_query-slow" \
  --alarm-description "Alert when RAG query takes > 10 seconds" \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=finsight-rag_query_handler \
  --statistic Average \
  --period 300 \
  --threshold 10000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: Lambda rag_query slow response"

# =============================================================================
# ALARM 5: API Gateway 5XX Errors
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-api-5xx-errors" \
  --alarm-description "Alert when API returns 5XX errors" \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value=finsight-ai-api \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: API Gateway 5XX errors"

# =============================================================================
# ALARM 6: API Gateway High Latency
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-api-high-latency" \
  --alarm-description "Alert when API latency > 15 seconds" \
  --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=finsight-ai-api \
  --statistic Average \
  --period 300 \
  --threshold 15000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: API Gateway high latency"

# =============================================================================
# ALARM 7: RDS CPU High
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-rds-cpu-high" \
  --alarm-description "Alert when RDS CPU > 80%" \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=finsight-ai-pgvector \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: RDS CPU high"

# =============================================================================
# ALARM 8: RDS Low Memory
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-rds-memory-low" \
  --alarm-description "Alert when RDS free memory < 100MB" \
  --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=finsight-ai-pgvector \
  --statistic Average \
  --period 300 \
  --threshold 100000000 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: RDS low memory"

# =============================================================================
# ALARM 9: RDS High Connections
# =============================================================================
aws cloudwatch put-metric-alarm \
  --alarm-name "finsight-rds-connections-high" \
  --alarm-description "Alert when RDS connections > 50" \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=finsight-ai-pgvector \
  --statistic Average \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions $SNS_TOPIC \
  --treat-missing-data notBreaching

echo "✅ Alarm: RDS high connections"

echo ""
echo "============================================"
echo "  All 9 CloudWatch Alarms Created!"
echo "============================================"
echo ""
echo "View alarms: AWS Console → CloudWatch → Alarms"
