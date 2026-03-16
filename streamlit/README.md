# FinSight AI - Streamlit Demo

A visual interface for your RAG-powered financial intelligence API.

![Demo](demo_screenshot.png)

## Quick Start (2 minutes)

### Step 1: Install dependencies

```bash
pip install streamlit requests
```

### Step 2: Update API Key

Edit `app.py` and replace:
```python
API_KEY = "YOUR_API_KEY_HERE"
```

With your actual API key:
```bash
# Get your API key
cd ~/finsight-ai/terraform
terraform output -raw api_key_value
```

### Step 3: Run the app

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## Features

✅ **Ask questions** about SEC filings
✅ **View sources** and confidence scores
✅ **Quick question buttons** for common queries
✅ **Raw API response** for debugging
✅ **Styled UI** with professional look

---

## Sample Questions

- What were Apple's revenue drivers?
- Summarize the 10-K filing
- What are the risk factors?
- How did iPhone sales perform?
- What is the company's debt situation?

---

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │
└────────┬────────┘
         │ HTTPS + API Key
         ▼
┌─────────────────┐
│  API Gateway    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda (RAG)   │
│  ├─ Bedrock     │
│  └─ pgvector    │
└─────────────────┘
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid API key" | Check API key in sidebar |
| "Connection error" | Verify API URL is correct |
| "Timeout" | Lambda cold start, try again |
| No results | Check if data exists in pgvector |

---

## Deploy to Cloud (Optional)

### Streamlit Cloud (Free)
1. Push to GitHub
2. Go to share.streamlit.io
3. Connect repo and deploy

### AWS EC2
```bash
# On EC2 instance
pip install streamlit requests
nohup streamlit run app.py --server.port 8501 &
```

---

**Built for FinSight AI | Mahendra Nali**
