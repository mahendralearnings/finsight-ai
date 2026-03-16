"""
ingest_market/handler.py
Fetches market data (prices, financials) via Yahoo Finance and stores in S3.
Triggered by EventBridge every 1 hour.
"""

import json
import os
import boto3
import urllib.request
from datetime import datetime, timezone

s3 = boto3.client("s3")

# Tickers to track
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "JPM",  "GS",   "BAC",   "WFC",  "MS",
    "NVDA", "TSLA", "BRK-B", "V",    "MA",
]

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
YAHOO_SUMMARY_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryDetail,financialData,defaultKeyStatistics"


def fetch_quote(ticker: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d&includePrePost=false"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data.get("chart", {}).get("result", [{}])[0]
        meta   = result.get("meta", {})
        return {
            "ticker":          ticker,
            "currency":        meta.get("currency"),
            "exchange":        meta.get("exchangeName"),
            "current_price":   meta.get("regularMarketPrice"),
            "previous_close":  meta.get("chartPreviousClose"),
            "52w_high":        meta.get("fiftyTwoWeekHigh"),
            "52w_low":         meta.get("fiftyTwoWeekLow"),
            "market_cap":      meta.get("marketCap"),
            "timestamps":      result.get("timestamp", []),
            "ohlcv":           result.get("indicators", {}).get("quote", [{}])[0],
        }
    except Exception as e:
        print(f"[WARN] Quote fetch failed for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e)}


# def fetch_fundamentals(ticker: str) -> dict:
#     """Fetch key financial fundamentals for a ticker."""
#     url = YAHOO_SUMMARY_URL.format(ticker=ticker)
#     req = urllib.request.Request(
#         url,
#         headers={
#             "User-Agent": "Mozilla/5.0",
#             "Accept":     "application/json",
#         }
#     )
#     try:
#         with urllib.request.urlopen(req, timeout=10) as resp:
#             data = json.loads(resp.read().decode("utf-8"))
#         result = data.get("quoteSummary", {}).get("result", [{}])[0]
#         fd     = result.get("financialData", {})
#         sd     = result.get("summaryDetail", {})
#         ks     = result.get("defaultKeyStatistics", {})
#         return {
#             "ticker":               ticker,
#             "pe_ratio":             sd.get("trailingPE", {}).get("raw"),
#             "forward_pe":           sd.get("forwardPE", {}).get("raw"),
#             "dividend_yield":       sd.get("dividendYield", {}).get("raw"),
#             "revenue":              fd.get("totalRevenue", {}).get("raw"),
#             "gross_profit":         fd.get("grossProfits", {}).get("raw"),
#             "ebitda":               fd.get("ebitda", {}).get("raw"),
#             "debt_to_equity":       fd.get("debtToEquity", {}).get("raw"),
#             "return_on_equity":     fd.get("returnOnEquity", {}).get("raw"),
#             "profit_margin":        fd.get("profitMargins", {}).get("raw"),
#             "revenue_growth":       fd.get("revenueGrowth", {}).get("raw"),
#             "earnings_growth":      fd.get("earningsGrowth", {}).get("raw"),
#             "beta":                 ks.get("beta", {}).get("raw"),
#             "shares_outstanding":   ks.get("sharesOutstanding", {}).get("raw"),
#         }
#     except Exception as e:
#         print(f"[WARN] Fundamentals fetch failed for {ticker}: {e}")
#         return {"ticker": ticker, "error": str(e)}


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
    date_str  = datetime.now(timezone.utc).strftime("%Y/%m/%d")

    print(f"[INFO] Starting market data ingestion for {len(TICKERS)} tickers")

    quotes       = []
    fundamentals = []

    for ticker in TICKERS:
        quotes.append(fetch_quote(ticker))
        #fundamentals.append(fetch_fundamentals(ticker))

    # Save quotes batch
    quotes_key = f"market_data/quotes/{date_str}/{timestamp}.json"
    save_to_s3({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "tickers":    TICKERS,
        "quotes":     quotes,
    }, bucket, quotes_key)

    # Save fundamentals batch
    fundamentals_key = f"market_data/fundamentals/{date_str}/{timestamp}.json"
    save_to_s3({
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
        "tickers":      TICKERS,
        "fundamentals": fundamentals,
    }, bucket, fundamentals_key)

    print(f"[INFO] Market ingestion complete — {len(TICKERS)} tickers processed")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":         "Market data ingestion complete",
            "tickers_fetched": len(TICKERS),
            "quotes_key":      quotes_key,
            "fundamentals_key": fundamentals_key,
            "timestamp":       timestamp,
        })
    }
