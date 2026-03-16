# 📊 FinSight AI

### Enterprise RAG Platform for Financial Intelligence

<p align="center">
  <img src="https://img.shields.io/badge/AWS-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white" alt="AWS"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white" alt="Terraform"/>
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Apache_Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white" alt="Airflow"/>
</p>

---

## 🎯 Overview

**FinSight AI** is a production-ready Retrieval-Augmented Generation (RAG) platform that transforms how financial analysts interact with SEC filings and market data. Instead of manually reading through hundreds of documents, users can ask natural language questions and receive accurate, source-cited answers in seconds.

### The Problem
Financial analysts spend hours reading through SEC filings to extract insights. What if they could just ask a question?

### The Solution
FinSight AI ingests SEC EDGAR filings, chunks and embeds them using Amazon Bedrock, stores vectors in PostgreSQL with pgvector, and answers natural language queries with source citations using Claude AI.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Intelligent Search** | Semantic search across 500+ SEC filings using vector embeddings |
| 🤖 **AI-Powered Answers** | Claude 3 Haiku generates accurate, contextual responses |
| 📊 **Source Citations** | Every answer includes document sources and confidence scores |
| ⚡ **Sub-3s Response** | Optimized pipeline delivers answers in under 3 seconds |
| 📈 **Production Monitoring** | CloudWatch dashboards and 9 proactive alarms |
| 💰 **Cost Optimized** | Serverless architecture runs at ~$0.50/day |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                   │
│     SEC EDGAR API      │      Yahoo Finance      │      News APIs          │
└────────────┬───────────┴───────────┬─────────────┴───────────┬──────────────┘
             │                       │                         │
             ▼                       ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS LAMBDA (Ingestion)                              │
│              ingest_sec    │    ingest_market    │    ingest_news          │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AMAZON S3 (Data Lake)                               │
│                    raw/    │    processed/    │    embeddings/             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS GLUE (ETL)                                      │
│                    Chunking    │    Cleaning    │    Transformation        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AMAZON BEDROCK                                      │
│              Titan Embeddings (1024-dim)    │    Claude 3 Haiku            │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RDS POSTGRESQL + PGVECTOR                           │
│                    Vector Storage    │    HNSW Indexing                    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY + LAMBDA                                │
│                    REST API    │    RAG Query Handler                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                                 │
│              Streamlit UI    │    curl/API    │    Web Apps                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Cloud Infrastructure (AWS)
| Service | Purpose |
|---------|---------|
| **Lambda** | Serverless compute for ingestion, embedding, and RAG |
| **S3** | Data lake for raw and processed documents |
| **RDS PostgreSQL** | Vector database with pgvector extension |
| **API Gateway** | RESTful API with authentication |
| **Bedrock** | Managed AI (Titan Embeddings + Claude 3) |
| **Glue** | ETL jobs for document processing |
| **CloudWatch** | Monitoring, dashboards, and alerting |
| **VPC** | Network isolation with private subnets |
| **Secrets Manager** | Secure credential management |

### DevOps & Orchestration
| Tool | Purpose |
|------|---------|
| **Terraform** | Infrastructure as Code |
| **Apache Airflow** | Workflow orchestration |
| **Docker** | Containerization |
| **GitHub Actions** | CI/CD (optional) |

---

## 📁 Project Structure

```
finsight-ai/
├── terraform/                    # Infrastructure as Code
│   ├── main.tf                   # Root module
│   ├── variables.tf              # Input variables
│   ├── outputs.tf                # Output values
│   └── modules/
│       ├── s3/                   # S3 buckets
│       ├── iam/                  # IAM roles & policies
│       ├── vpc/                  # VPC & networking
│       ├── rds/                  # PostgreSQL + pgvector
│       ├── lambda_functions/     # Lambda functions
│       ├── api_gateway/          # API Gateway
│       └── secrets_manager/      # Secrets
│
├── lambda/                       # Lambda function code
│   ├── ingest_sec/
│   │   └── handler.py
│   ├── ingest_market/
│   │   └── handler.py
│   ├── embed_documents/
│   │   └── handler.py
│   └── rag_query_handler/
│       └── handler.py
│
├── glue/                         # Glue ETL jobs
│   ├── process_sec_filings.py
│   ├── process_market_data.py
│   └── process_news.py
│
├── airflow/                      # Airflow orchestration
│   ├── docker-compose.yml
│   ├── dags/
│   │   ├── finsight_sec_ingestion.py
│   │   └── finsight_full_pipeline.py
│   └── plugins/
│
├── streamlit/                    # Demo UI
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
│
├── monitoring/                   # CloudWatch setup
│   ├── cloudwatch-dashboard.json
│   └── create-alarms.sh
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── TROUBLESHOOTING.md
│
├── .gitignore
├── README.md
└── LICENSE
```

---

## 🚀 Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Terraform >= 1.0
- Docker & Docker Compose
- Python 3.12

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/finsight-ai.git
cd finsight-ai
```

### 2. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 3. Start Airflow

```bash
cd ../airflow
docker-compose up -d
```

### 4. Access Services

| Service | URL |
|---------|-----|
| Airflow UI | http://localhost:8080 (admin/admin) |
| API Gateway | Check Terraform output |
| Streamlit | http://localhost:8501 |

### 5. Test the API

```bash
# Get API details
cd terraform
API_URL=$(terraform output -raw api_query_endpoint)
API_KEY=$(terraform output -raw api_key_value)

# Send a query
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"query": "What were Apple revenue drivers in 2023?"}'
```

---

## 📊 Sample Query & Response

### Request
```bash
curl -X POST "https://api.finsight.ai/query" \
  -H "x-api-key: $API_KEY" \
  -d '{"query": "What were Apple revenue drivers?"}'
```

### Response
```json
{
  "answer": "According to the SEC filings, Apple's key revenue drivers in fiscal year 2023 were: 1) iPhone revenue grew 2% year-over-year to $200 billion. 2) Services revenue reached $85 billion, representing 22% of total revenue.",
  "sources": ["sec_filings/AAPL/10-K_2023.json"],
  "chunks": 3,
  "similarity": 0.89,
  "processing_time_ms": 2340
}
```

---

## 📈 Monitoring

### CloudWatch Dashboard

The dashboard provides real-time visibility into:
- Lambda invocations and errors
- API Gateway requests and latency
- RDS CPU, memory, and connections
- Bedrock model usage

### CloudWatch Alarms (9 Total)

| Alarm | Trigger | Action |
|-------|---------|--------|
| Lambda Errors | > 3 in 5 min | SNS Email |
| Lambda Slow | > 10 sec avg | SNS Email |
| API 5XX | > 5 in 5 min | SNS Email |
| API Latency | > 15 sec avg | SNS Email |
| RDS CPU | > 80% | SNS Email |
| RDS Memory | < 100MB | SNS Email |
| RDS Connections | > 50 | SNS Email |

---

## 💰 Cost Analysis

### Daily Cost (Active Development)
| Service | Cost |
|---------|------|
| RDS (t3.micro) | ~$0.50 |
| VPC Endpoints | ~$0.50 |
| Lambda | ~$0.01 |
| S3 | ~$0.01 |
| **Total** | **~$1.02/day** |

### Cost Optimization Strategies
- Stop RDS when not in use (`aws rds stop-db-instance`)
- Delete VPC endpoints during breaks
- Use Glue Python Shell (1/16 DPU) instead of Spark
- Serverless architecture = pay only for usage

---

## 🔧 Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Vector DB | pgvector vs Pinecone | Lower cost, SQL familiarity, hybrid queries |
| Embeddings | Titan vs OpenAI | Data stays in AWS, VPC endpoint access |
| LLM | Claude 3 Haiku | Fast, accurate, cost-effective |
| Infra | Terraform vs CDK | Multi-cloud ready, declarative |
| Orchestration | Airflow vs Step Functions | Visual DAGs, Python native |

---

## 📚 Documentation

- [Architecture Deep Dive](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [API Reference](docs/API.md)

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Mahendra Nali**

Building AI-powered solutions on AWS | GenAI | RAG | Cloud Architecture

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://linkedin.com/in/yourprofile)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/yourprofile)

---

<p align="center">Built with ❤️ using AWS, Python, and Terraform</p>
