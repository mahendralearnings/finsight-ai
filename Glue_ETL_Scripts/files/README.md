# FinSight AI - Glue Python Shell Jobs (Cost-Optimized)

## Cost Comparison

| Job Type | DPU | Cost/Run (5 min) |
|----------|-----|------------------|
| Spark (2 × G.1X) | 2.0 | ~$0.15 |
| **Python Shell** | 0.0625 | **~$0.01** |

**Savings: 93%** 🎉

---

## Step 1: Upload Scripts to S3

```bash
aws s3 cp process_sec_filings.py s3://finsight-ai-raw-617297630012/glue_scripts/
aws s3 cp process_market_data.py s3://finsight-ai-raw-617297630012/glue_scripts/
aws s3 cp process_news.py s3://finsight-ai-raw-617297630012/glue_scripts/

# Verify
aws s3 ls s3://finsight-ai-raw-617297630012/glue_scripts/
```

---

## Step 2: Create IAM Role (if not exists)

```bash
# Check if role exists
aws iam get-role --role-name finsight-ai-glue-role

# If not, create it:
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

aws iam attach-role-policy \
  --role-name finsight-ai-glue-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

aws iam attach-role-policy \
  --role-name finsight-ai-glue-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

---

## Step 3: Create Python Shell Job (Console)

### Job 1: Process SEC Filings

1. Go to **AWS Glue Console** → **ETL Jobs** → **Create job**
2. Select **Python Shell script editor**
3. Choose **Upload and edit an existing script**
4. Click **Create**

**Job Details (in right panel):**

| Setting | Value |
|---------|-------|
| **Name** | `finsight-process-sec-filings` |
| **IAM Role** | `finsight-ai-glue-role` |
| **Python version** | `Python 3.9` |
| **Data processing units** | `0.0625 DPU` ← Cheapest! |
| **Script filename** | `s3://finsight-ai-raw-617297630012/glue_scripts/process_sec_filings.py` |
| **Timeout** | `10 minutes` |

**Job parameters** (Advanced properties → Job parameters):

| Key | Value |
|-----|-------|
| `--source_bucket` | `finsight-ai-raw-617297630012` |
| `--target_bucket` | `finsight-ai-processed-617297630012` |
| `--account_id` | `617297630012` |

5. Click **Save** → **Run**

---

### Job 2: Process Market Data

Same steps, different name and script:

| Setting | Value |
|---------|-------|
| **Name** | `finsight-process-market-data` |
| **Script** | `s3://finsight-ai-raw-617297630012/glue_scripts/process_market_data.py` |

Same job parameters as above.

---

### Job 3: Process News

| Setting | Value |
|---------|-------|
| **Name** | `finsight-process-news` |
| **Script** | `s3://finsight-ai-raw-617297630012/glue_scripts/process_news.py` |

Same job parameters as above.

---

## Step 4: Verify Sample Data Exists

Before running, ensure you have data in the raw bucket:

```bash
# Check for SEC filings
aws s3 ls s3://finsight-ai-raw-617297630012/sec_filings/ --recursive

# Check for market data
aws s3 ls s3://finsight-ai-raw-617297630012/market_data/ --recursive

# Check for news
aws s3 ls s3://finsight-ai-raw-617297630012/news/ --recursive
```

If empty, your ingest Lambdas need to run first, or upload sample data.

---

## Step 5: Run Jobs

### From Console:
1. Go to **Glue** → **ETL Jobs**
2. Click on job name
3. Click **Run**
4. Monitor in **Runs** tab

### From CLI:
```bash
# Run job
aws glue start-job-run --job-name finsight-process-sec-filings

# Check status
aws glue get-job-runs --job-name finsight-process-sec-filings --max-items 1
```

---

## Step 6: Verify Output

```bash
# Check processed SEC filings
aws s3 ls s3://finsight-ai-processed-617297630012/sec_filings/

# Check processed market data
aws s3 ls s3://finsight-ai-processed-617297630012/market_data/

# Check processed news
aws s3 ls s3://finsight-ai-processed-617297630012/news/

# View a processed file
aws s3 cp s3://finsight-ai-processed-617297630012/sec_filings/AAPL/chunks.json - | head -100
```

---

## Cost Tracking

After running jobs, check costs:

1. **AWS Cost Explorer** → Service: AWS Glue
2. **Glue Console** → **ETL Jobs** → Click job → **Runs** tab
   - See DPU-hours used per run

**Expected cost per run:** ~$0.01 (at 0.0625 DPU × 5 min)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Role not found" | Create IAM role (Step 2) |
| "Script not found" | Verify S3 path is correct |
| "Access denied to S3" | Attach S3FullAccess to role |
| "No files processed" | Check if raw bucket has data |

### View Logs:
```bash
# Get log group
aws logs describe-log-groups --log-group-name-prefix /aws-glue/python-jobs

# Tail logs
aws logs tail /aws-glue/python-jobs/output --follow
```

---

## Data Flow After ETL

```
S3 Raw                          S3 Processed
├── sec_filings/                ├── sec_filings/
│   └── AAPL/10k.json    ──►    │   ├── AAPL/chunks.json
│                               │   └── _all_chunks.json
├── market_data/                ├── market_data/
│   └── AAPL/prices.json ──►    │   ├── AAPL/prices_normalized.json
│                               │   └── _summary.json
└── news/                       └── news/
    └── AAPL/articles.json ──►      ├── AAPL/articles_processed.json
                                    ├── _all_chunks.json
                                    └── _summary.json
```

**Next:** Trigger `embed_documents` Lambda on processed chunks!
