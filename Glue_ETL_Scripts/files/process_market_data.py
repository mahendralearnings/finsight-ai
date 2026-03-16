"""
FinSight AI - Glue Python Shell Job: Process Market Data
Transforms raw Yahoo Finance data into normalized format for analysis.

Job Type: Python Shell (0.0625 DPU - ~$0.01/run)
"""

import sys
import json
import boto3
from datetime import datetime

# -----------------------------------------------------------------------------
# Get Job Parameters
# -----------------------------------------------------------------------------
args = {}
for i, arg in enumerate(sys.argv):
    if arg.startswith('--'):
        key = arg[2:]
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
            args[key] = sys.argv[i + 1]

SOURCE_BUCKET = args.get('source_bucket', 'finsight-ai-raw-617297630012')
TARGET_BUCKET = args.get('target_bucket', 'finsight-ai-processed-617297630012')

print(f"Starting Market Data ETL Job (Python Shell)")
print(f"Source: s3://{SOURCE_BUCKET}/market_data/")
print(f"Target: s3://{TARGET_BUCKET}/market_data/")

# -----------------------------------------------------------------------------
# Processing Functions
# -----------------------------------------------------------------------------
def calculate_indicators(prices):
    """Calculate technical indicators from price data."""
    if len(prices) < 5:
        return prices
    
    prices = sorted(prices, key=lambda x: x.get('date', ''))
    
    for i, price in enumerate(prices):
        close = price.get('close', 0)
        
        # 5-day SMA
        if i >= 4:
            sma_5 = sum(p.get('close', 0) for p in prices[i-4:i+1]) / 5
            price['sma_5'] = round(sma_5, 2)
        
        # 20-day SMA
        if i >= 19:
            sma_20 = sum(p.get('close', 0) for p in prices[i-19:i+1]) / 20
            price['sma_20'] = round(sma_20, 2)
        
        # Daily return
        if i > 0:
            prev_close = prices[i-1].get('close', 0)
            if prev_close > 0:
                daily_return = (close - prev_close) / prev_close * 100
                price['daily_return_pct'] = round(daily_return, 4)
    
    return prices

def normalize_yahoo_data(raw_data, ticker):
    """Normalize Yahoo Finance data structure."""
    normalized = []
    
    if 'chart' in raw_data:
        # v8/chart endpoint format
        result = raw_data['chart'].get('result', [{}])[0]
        timestamps = result.get('timestamp', [])
        quotes = result.get('indicators', {}).get('quote', [{}])[0]
        
        for i, ts in enumerate(timestamps):
            try:
                normalized.append({
                    'ticker': ticker,
                    'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                    'timestamp': ts,
                    'open': round(quotes.get('open', [])[i] or 0, 2),
                    'high': round(quotes.get('high', [])[i] or 0, 2),
                    'low': round(quotes.get('low', [])[i] or 0, 2),
                    'close': round(quotes.get('close', [])[i] or 0, 2),
                    'volume': int(quotes.get('volume', [])[i] or 0),
                })
            except (IndexError, TypeError):
                continue
    
    elif 'prices' in raw_data:
        for price in raw_data['prices']:
            ts = price.get('timestamp', price.get('date', 0))
            normalized.append({
                'ticker': ticker,
                'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d') if isinstance(ts, (int, float)) else ts,
                'open': round(price.get('open', 0), 2),
                'high': round(price.get('high', 0), 2),
                'low': round(price.get('low', 0), 2),
                'close': round(price.get('close', 0), 2),
                'volume': int(price.get('volume', 0)),
            })
    
    elif isinstance(raw_data, list):
        for price in raw_data:
            normalized.append({
                'ticker': ticker,
                'date': price.get('date', ''),
                'open': round(price.get('open', 0), 2),
                'high': round(price.get('high', 0), 2),
                'low': round(price.get('low', 0), 2),
                'close': round(price.get('close', 0), 2),
                'volume': int(price.get('volume', 0)),
            })
    
    return normalized

def generate_summary(prices, ticker):
    """Generate summary statistics."""
    if not prices:
        return {}
    
    closes = [p['close'] for p in prices if p.get('close', 0) > 0]
    
    if not closes:
        return {}
    
    return {
        'ticker': ticker,
        'data_points': len(prices),
        'date_range': {
            'start': prices[0].get('date', ''),
            'end': prices[-1].get('date', '')
        },
        'price_stats': {
            'latest': closes[-1],
            'min': round(min(closes), 2),
            'max': round(max(closes), 2),
            'mean': round(sum(closes) / len(closes), 2),
            'change_pct': round((closes[-1] - closes[0]) / closes[0] * 100, 2) if closes[0] > 0 else 0
        },
        'processed_at': datetime.now().isoformat()
    }

# -----------------------------------------------------------------------------
# Main ETL Logic
# -----------------------------------------------------------------------------
s3_client = boto3.client('s3')

paginator = s3_client.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=SOURCE_BUCKET, Prefix='market_data/')

all_summaries = []
files_processed = 0
files_failed = 0

for page in pages:
    for obj in page.get('Contents', []):
        key = obj['Key']
        
        if not key.endswith('.json'):
            continue
        
        try:
            print(f"Processing: {key}")
            
            # Extract ticker from path
            parts = key.split('/')
            ticker = parts[1] if len(parts) > 1 else 'UNKNOWN'
            
            response = s3_client.get_object(Bucket=SOURCE_BUCKET, Key=key)
            content = response['Body'].read().decode('utf-8')
            raw_data = json.loads(content)
            
            # Normalize and add indicators
            normalized = normalize_yahoo_data(raw_data, ticker)
            print(f"  Normalized {len(normalized)} price records")
            
            if normalized:
                normalized = calculate_indicators(normalized)
            
            # Generate summary
            summary = generate_summary(normalized, ticker)
            if summary:
                all_summaries.append(summary)
            
            # Write normalized data
            output_key = f"market_data/{ticker}/prices_normalized.json"
            s3_client.put_object(
                Bucket=TARGET_BUCKET,
                Key=output_key,
                Body=json.dumps({
                    'ticker': ticker,
                    'record_count': len(normalized),
                    'processed_at': datetime.now().isoformat(),
                    'summary': summary,
                    'prices': normalized
                }, indent=2),
                ContentType='application/json'
            )
            
            print(f"  Written to s3://{TARGET_BUCKET}/{output_key}")
            files_processed += 1
            
        except Exception as e:
            print(f"  Error: {str(e)}")
            files_failed += 1

# Write summary
if all_summaries:
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key="market_data/_summary.json",
        Body=json.dumps({
            'tickers_processed': len(all_summaries),
            'generated_at': datetime.now().isoformat(),
            'summaries': all_summaries
        }, indent=2),
        ContentType='application/json'
    )
    print(f"Written market summary to s3://{TARGET_BUCKET}/market_data/_summary.json")

print(f"\nProcessing complete:")
print(f"  Files processed: {files_processed}")
print(f"  Files failed: {files_failed}")
print("Job completed successfully!")
