# FinSight AI - Glue ETL Jobs Setup Guide

## Overview

Three Glue ETL jobs for processing financial data:

| Job | Input | Output | Purpose |
|-----|-------|--------|---------|
| `process_sec_filings` | Raw SEC 10-K/10-Q | Chunked documents | Ready for embedding |
| `process_market_data` | Yahoo Finance OHLCV | Normalized + indicators | Analysis ready |
| `process_news` | News articles | Sentiment + chunks | Ready for embedding |

---

## Step 1: Upload Scripts to S3

```bash
# Create scripts folder in your raw bucket
aws s3 cp process_sec_filings.py s3://finsight-ai-raw-617297630012/glue_scripts/
aws s3 cp process_market_data.py s3://finsight-ai-raw-617297630012/glue_scripts/
aws s3 cp process_news.py s3://finsight-ai-raw-617297630012/glue_scripts/
```

---

## Step 2: Create IAM Role for Glue

If you don't have a Glue role yet:

```bash
# Create role via CLI (or use existing finsight-ai-glue-role)
aws iam create-role \
  --role-name finsight-ai-glue-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "glue.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name finsight-ai-glue-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

aws iam attach-role-policy \
  --role-name finsight-ai-glue-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

---

## Step 3: Create Glue Jobs (Console)

### Job 1: Process SEC Filings

1. Go to **AWS Glue** → **ETL Jobs** → **Create job**
2. Select **Spark script editor** → **Create a new script with boilerplate code**
3. Click **Create**

**Configure:**

| Setting | Value |
|---------|-------|
| **Name** | `finsight-process-sec-filings` |
| **IAM Role** | `finsight-ai-glue-role` |
| **Type** | `Spark` |
| **Glue version** | `Glue 4.0` |
| **Language** | `Python 3` |
| **Script path** | `s3://finsight-ai-raw-617297630012/glue_scripts/process_sec_filings.py` |
| **Worker type** | `G.1X` (cost-effective) |
| **Number of workers** | `2` |
| **Job timeout** | `30 minutes` |

**Job parameters** (click Advanced → Job parameters):

| Key | Value |
|-----|-------|
| `--source_bucket` | `finsight-ai-raw-617297630012` |
| `--target_bucket` | `finsight-ai-processed-617297630012` |
| `--account_id` | `617297630012` |

4. Click **Save** → **Run**

---

### Job 2: Process Market Data

Same steps, but:

| Setting | Value |
|---------|-------|
| **Name** | `finsight-process-market-data` |
| **Script path** | `s3://finsight-ai-raw-617297630012/glue_scripts/process_market_data.py` |

Same job parameters.

---

### Job 3: Process News

Same steps, but:

| Setting | Value |
|---------|-------|
| **Name** | `finsight-process-news` |
| **Script path** | `s3://finsight-ai-raw-617297630012/glue_scripts/process_news.py` |

Same job parameters.

---

## Step 4: Test the Jobs

### Add Sample Data First

```bash
# Upload sample SEC filing
aws s3 cp test_data/sec_sample.json s3://finsight-ai-raw-617297630012/sec_filings/AAPL/10k_2024.json

# Upload sample market data  
aws s3 cp test_data/market_sample.json s3://finsight-ai-raw-617297630012/market_data/AAPL/prices.json

# Upload sample news
aws s3 cp test_data/news_sample.json s3://finsight-ai-raw-617297630012/news/AAPL/articles.json
```

### Run Jobs

```bash
# Run via CLI
aws glue start-job-run --job-name finsight-process-sec-filings
aws glue start-job-run --job-name finsight-process-market-data
aws glue start-job-run --job-name finsight-process-news
```

### Check Output

```bash
# Verify processed files
aws s3 ls s3://finsight-ai-processed-617297630012/sec_filings/
aws s3 ls s3://finsight-ai-processed-617297630012/market_data/
aws s3 ls s3://finsight-ai-processed-617297630012/news/
```

---

## Step 5: Set Up Triggers (Optional)

### S3 Event Trigger

When new files land in raw bucket, automatically run ETL:

1. Go to **Glue** → **Triggers** → **Add trigger**
2. **Name:** `trigger-sec-processing`
3. **Trigger type:** `On-demand` or `Scheduled`
4. **Jobs to trigger:** `finsight-process-sec-filings`

### Scheduled Trigger (Daily)

1. **Trigger type:** `Scheduled`
2. **Frequency:** `Daily`
3. **Start time:** `02:00 UTC` (off-peak)

---

## Data Flow After ETL

```
S3 Processed Bucket
├── sec_filings/
│   ├── AAPL/chunks.json          ← Ready for embed_documents Lambda
│   └── _all_chunks.json          ← Consolidated for batch embedding
├── market_data/
│   ├── AAPL/prices_normalized.json
│   └── _summary.json
└── news/
    ├── AAPL/articles_processed.json
    ├── _all_chunks.json          ← Ready for embed_documents Lambda
    └── _summary.json
```

---

## Monitoring

### CloudWatch Logs

```bash
# View job logs
aws logs tail /aws-glue/jobs/finsight-process-sec-filings --follow
```

### Glue Console

- **ETL Jobs** → Click job → **Runs** tab
- View run status, duration, DPU usage

---

## Cost Estimate

| Job | Workers | Duration | Cost/Run |
|-----|---------|----------|----------|
| SEC Filings | 2 × G.1X | ~5 min | ~$0.15 |
| Market Data | 2 × G.1X | ~3 min | ~$0.10 |
| News | 2 × G.1X | ~5 min | ~$0.15 |

**Daily total:** ~$0.40 (if running all 3 once/day)

---

## Next: Codify in Terraform

Once jobs are tested and working, use the Terraform module in `terraform/modules/glue/` to make them infrastructure-as-code.
