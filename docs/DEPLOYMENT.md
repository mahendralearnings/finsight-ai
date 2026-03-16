# 🚀 FinSight AI - Deployment Guide

## Prerequisites

### Required Tools

| Tool | Version | Installation |
|------|---------|--------------|
| AWS CLI | 2.x | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"` |
| Terraform | >= 1.0 | `brew install terraform` or [tfenv](https://github.com/tfutils/tfenv) |
| Docker | 20.x+ | [Docker Install](https://docs.docker.com/get-docker/) |
| Docker Compose | 2.x | Included with Docker Desktop |
| Python | 3.12 | `pyenv install 3.12` |

### AWS Permissions

Your AWS user/role needs these permissions:
- `AmazonS3FullAccess`
- `AmazonRDSFullAccess`
- `AWSLambda_FullAccess`
- `AmazonAPIGatewayAdministrator`
- `AmazonVPCFullAccess`
- `IAMFullAccess`
- `SecretsManagerReadWrite`
- `AmazonBedrockFullAccess`
- `AWSGlueConsoleFullAccess`
- `CloudWatchFullAccess`

---

## Step 1: AWS Configuration

```bash
# Configure AWS CLI
aws configure

# Verify
aws sts get-caller-identity
```

---

## Step 2: Enable Bedrock Models

1. Go to **AWS Console** → **Amazon Bedrock**
2. Click **Model access** in the left sidebar
3. Request access to:
   - `Amazon Titan Embed Text V2`
   - `Anthropic Claude 3 Haiku`
4. Wait for approval (usually instant)

---

## Step 3: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Copy and edit variables
cp example.tfvars terraform.tfvars
nano terraform.tfvars  # Edit with your values

# Preview changes
terraform plan

# Deploy (takes ~10-15 minutes)
terraform apply

# Save outputs
terraform output > ../outputs.txt
```

### Expected Resources Created

| Resource | Count |
|----------|-------|
| S3 Buckets | 3 |
| Lambda Functions | 4 |
| RDS Instance | 1 |
| API Gateway | 1 |
| VPC Endpoints | 3 |
| IAM Roles | 4 |
| Security Groups | 3 |
| CloudWatch Alarms | 9 |

---

## Step 4: Build Lambda Layers

```bash
# Create psycopg2 layer for PostgreSQL connectivity
mkdir -p lambda_layers/psycopg2/python
cd lambda_layers/psycopg2

pip install psycopg2-binary \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target python/

zip -r ../psycopg2-layer.zip python/
cd ../..

# Upload to AWS
aws lambda publish-layer-version \
  --layer-name finsight-psycopg2 \
  --zip-file fileb://lambda_layers/psycopg2-layer.zip \
  --compatible-runtimes python3.12
```

---

## Step 5: Deploy Glue Jobs

```bash
# Upload Glue scripts to S3
aws s3 cp glue/process_sec_filings.py s3://finsight-ai-raw-YOUR_ACCOUNT_ID/glue_scripts/
aws s3 cp glue/process_market_data.py s3://finsight-ai-raw-YOUR_ACCOUNT_ID/glue_scripts/
aws s3 cp glue/process_news.py s3://finsight-ai-raw-YOUR_ACCOUNT_ID/glue_scripts/
```

Create Glue jobs via Console:
1. **AWS Console** → **Glue** → **ETL Jobs**
2. Create Python Shell job
3. Set DPU to **1/16** (cost optimization)
4. Point to S3 script path

---

## Step 6: Start Airflow

```bash
cd airflow

# Set permissions
chmod -R 777 logs/ dags/

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f airflow-webserver
```

Access: **http://localhost:8080** (admin/admin)

---

## Step 7: Set Up Monitoring

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "FinSight-AI-Dashboard" \
  --dashboard-body file://monitoring/cloudwatch-dashboard.json

# Create alarms
chmod +x monitoring/create-alarms.sh
./monitoring/create-alarms.sh
```

---

## Step 8: Run Initial Data Pipeline

### Option A: Via Airflow UI
1. Open http://localhost:8080
2. Enable `finsight_sec_ingestion` DAG
3. Click **Trigger DAG**

### Option B: Via CLI
```bash
docker-compose exec airflow-webserver \
  airflow dags trigger finsight_sec_ingestion
```

---

## Step 9: Test the API

```bash
# Get credentials
cd terraform
API_URL=$(terraform output -raw api_query_endpoint)
API_KEY=$(terraform output -raw api_key_value)

# Test query
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"query": "What were Apple revenue drivers?"}'
```

---

## Step 10: Start Streamlit Demo (Optional)

```bash
cd streamlit

# Create .env file
cp .env.example .env
nano .env  # Add your API_URL and API_KEY

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run app.py
```

Access: **http://localhost:8501**

---

## 🛑 Stopping Services

### Daily Shutdown (Save Costs)

```bash
# Stop RDS
aws rds stop-db-instance --db-instance-identifier finsight-ai-pgvector

# Stop Airflow
cd airflow && docker-compose down
```

### Delete VPC Endpoints (Optional - Saves $15/month)

```bash
ENDPOINTS=$(aws ec2 describe-vpc-endpoints \
  --query 'VpcEndpoints[?VpcEndpointType==`Interface`].VpcEndpointId' \
  --output text)
aws ec2 delete-vpc-endpoints --vpc-endpoint-ids $ENDPOINTS
```

---

## ▶️ Resuming Services

```bash
# Start RDS
aws rds start-db-instance --db-instance-identifier finsight-ai-pgvector

# Wait for RDS to be available
aws rds wait db-instance-available --db-instance-identifier finsight-ai-pgvector

# Start Airflow
cd airflow && docker-compose up -d
```

---

## 🗑️ Complete Teardown

```bash
cd terraform
terraform destroy
```

⚠️ This deletes ALL resources including data!

---

## 🐛 Troubleshooting

### Lambda Can't Connect to RDS
- Check VPC endpoint for Secrets Manager exists
- Verify Lambda is in the same VPC as RDS
- Check security group allows port 5432

### Airflow DAG Not Visible
- Check for Python syntax errors: `docker-compose exec airflow-webserver airflow dags list-import-errors`
- Restart scheduler: `docker-compose restart airflow-scheduler`

### API Returns 403
- Verify API key is correct
- Check API Gateway stage is deployed

### Bedrock Access Denied
- Ensure model access is approved in Bedrock console
- Check Lambda IAM role has `bedrock:InvokeModel` permission

---

## 📞 Support

If you encounter issues:
1. Check CloudWatch Logs for detailed errors
2. Review the [Troubleshooting Guide](TROUBLESHOOTING.md)
3. Open a GitHub issue with logs and steps to reproduce
