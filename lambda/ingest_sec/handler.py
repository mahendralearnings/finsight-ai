"""
ingest_sec/handler.py
Fetches SEC EDGAR filings and stores raw JSON in S3.
Triggered by EventBridge every 6 hours.
"""

import json
import os
import boto3
import urllib.request
import urllib.parse
from datetime import datetime, timezone

s3 = boto3.client("s3")
secrets = boto3.client("secretsmanager", region_name=os.environ.get("REGION", "us-east-1"))

# SEC EDGAR full-text search API (no auth required for public filings)
EDGAR_BASE_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22annual+report%22&dateRange=custom&startdt={start}&enddt={end}&forms=10-K,10-Q,8-K"

# Target companies (CIK numbers for major financial firms)
TARGET_COMPANIES = {
    "AAPL":  "0000320193",
    "MSFT":  "0000789019",
    "GOOGL": "0001652044",
    "AMZN":  "0001018724",
    "META":  "0001326801",
    "JPM":   "0000019617",
    "GS":    "0000886982",
}


def fetch_recent_filings(cik: str, ticker: str) -> list:
    """Fetch recent 10-K and 10-Q filings for a company from SEC EDGAR."""
    url = (
        f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FinSightAI research@finsight.ai"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        dates   = filings.get("filingDate", [])
        accnos  = filings.get("accessionNumber", [])
        docs    = filings.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form in ("10-K", "10-Q", "8-K"):
                results.append({
                    "ticker":           ticker,
                    "cik":              cik,
                    "form":             form,
                    "filing_date":      dates[i] if i < len(dates) else "",
                    "accession_number": accnos[i] if i < len(accnos) else "",
                    "primary_document": docs[i]  if i < len(docs)  else "",
                })
                if len(results) >= 10:   # last 10 filings per company
                    break
        return results

    except Exception as e:
        print(f"[WARN] Failed to fetch filings for {ticker} ({cik}): {e}")
        return []


def save_to_s3(data: dict, bucket: str, key: str) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType="application/json",
    )
    print(f"[INFO] Saved → s3://{bucket}/{key}")


def lambda_handler(event, context):
    bucket    = os.environ["S3_RAW_BUCKET"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    total     = 0

    print(f"[INFO] Starting SEC EDGAR ingestion at {timestamp}")

    for ticker, cik in TARGET_COMPANIES.items():
        filings = fetch_recent_filings(cik, ticker)
        if not filings:
            continue

        payload = {
            "ticker":     ticker,
            "cik":        cik,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "filings":    filings,
        }

        key = f"sec_filings/{ticker}/{timestamp}.json"
        save_to_s3(payload, bucket, key)
        total += len(filings)

    print(f"[INFO] Ingestion complete — {total} filings across {len(TARGET_COMPANIES)} companies")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":          "SEC ingestion complete",
            "filings_ingested": total,
            "timestamp":        timestamp,
        })
    }
