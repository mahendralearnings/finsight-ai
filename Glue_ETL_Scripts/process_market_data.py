"""
FinSight AI - Glue ETL Job: Process Market Data
Transforms raw Yahoo Finance data into normalized format for analysis.

Input:  s3://finsight-ai-raw-{account_id}/market_data/{ticker}/prices.json
Output: s3://finsight-ai-processed-{account_id}/market_data/{ticker}/prices_normalized.json
"""

import sys
import json
import boto3
from datetime import datetime
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_bucket',
    'target_bucket',
    'account_id'
])

job.init(args['JOB_NAME'], args)

SOURCE_BUCKET = args['source_bucket']
TARGET_BUCKET = args['target_bucket']
ACCOUNT_ID = args['account_id']

# -----------------------------------------------------------------------------
# Data Processing Functions
# -----------------------------------------------------------------------------

def calculate_technical_indicators(prices):
    """
    Calculate common technical indicators from price data.
    """
    if len(prices) < 20:
        return prices
    
    # Sort by date
    prices = sorted(prices, key=lambda x: x.get('date', ''))
    
    for i, price in enumerate(prices):
        close = price.get('close', 0)
        
        # Simple Moving Averages
        if i >= 4:
            sma_5 = sum(p.get('close', 0) for p in prices[i-4:i+1]) / 5
            price['sma_5'] = round(sma_5, 2)
        
        if i >= 19:
            sma_20 = sum(p.get('close', 0) for p in prices[i-19:i+1]) / 20
            price['sma_20'] = round(sma_20, 2)
        
        # Daily return
        if i > 0:
            prev_close = prices[i-1].get('close', 0)
            if prev_close > 0:
                daily_return = (close - prev_close) / prev_close * 100
                price['daily_return_pct'] = round(daily_return, 4)
        
        # Volatility (20-day rolling std of returns)
        if i >= 20:
            returns = []
            for j in range(i-19, i+1):
                if j > 0:
                    prev = prices[j-1].get('close', 0)
                    curr = prices[j].get('close', 0)
                    if prev > 0:
                        returns.append((curr - prev) / prev)
            
            if returns:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                volatility = variance ** 0.5 * (252 ** 0.5) * 100  # Annualized
                price['volatility_20d'] = round(volatility, 2)
    
    return prices

def normalize_yahoo_data(raw_data, ticker):
    """
    Normalize Yahoo Finance data structure.
    """
    normalized = []
    
    # Handle different Yahoo Finance response formats
    if 'chart' in raw_data:
        # v8/chart endpoint format
        result = raw_data['chart'].get('result', [{}])[0]
        timestamps = result.get('timestamp', [])
        quotes = result.get('indicators', {}).get('quote', [{}])[0]
        
        for i, ts in enumerate(timestamps):
            try:
                price_data = {
                    'ticker': ticker,
                    'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                    'timestamp': ts,
                    'open': round(quotes.get('open', [])[i] or 0, 2),
                    'high': round(quotes.get('high', [])[i] or 0, 2),
                    'low': round(quotes.get('low', [])[i] or 0, 2),
                    'close': round(quotes.get('close', [])[i] or 0, 2),
                    'volume': int(quotes.get('volume', [])[i] or 0),
                }
                
                # Calculate VWAP approximation
                if price_data['volume'] > 0:
                    typical_price = (price_data['high'] + price_data['low'] + price_data['close']) / 3
                    price_data['vwap'] = round(typical_price, 2)
                
                normalized.append(price_data)
            except (IndexError, TypeError) as e:
                continue
    
    elif 'prices' in raw_data:
        # Alternative format
        for price in raw_data['prices']:
            if 'date' in price or 'timestamp' in price:
                ts = price.get('timestamp', price.get('date', 0))
                normalized.append({
                    'ticker': ticker,
                    'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d') if isinstance(ts, (int, float)) else ts,
                    'timestamp': ts,
                    'open': round(price.get('open', 0), 2),
                    'high': round(price.get('high', 0), 2),
                    'low': round(price.get('low', 0), 2),
                    'close': round(price.get('close', 0), 2),
                    'volume': int(price.get('volume', 0)),
                })
    
    elif isinstance(raw_data, list):
        # Direct list format
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

def generate_summary_stats(prices, ticker):
    """
    Generate summary statistics for the price data.
    """
    if not prices:
        return {}
    
    closes = [p['close'] for p in prices if p.get('close', 0) > 0]
    volumes = [p['volume'] for p in prices if p.get('volume', 0) > 0]
    
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
            'latest': closes[-1] if closes else 0,
            'min': round(min(closes), 2),
            'max': round(max(closes), 2),
            'mean': round(sum(closes) / len(closes), 2),
            'change_pct': round((closes[-1] - closes[0]) / closes[0] * 100, 2) if closes[0] > 0 else 0
        },
        'volume_stats': {
            'avg_daily': int(sum(volumes) / len(volumes)) if volumes else 0,
            'max_daily': max(volumes) if volumes else 0
        },
        'processed_at': datetime.now().isoformat()
    }

# -----------------------------------------------------------------------------
# Main ETL Logic
# -----------------------------------------------------------------------------
print(f"Starting Market Data ETL Job")
print(f"Source: s3://{SOURCE_BUCKET}/market_data/")
print(f"Target: s3://{TARGET_BUCKET}/market_data/")

s3_client = boto3.client('s3')

# List all market data files
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
            
            # Read file
            response = s3_client.get_object(Bucket=SOURCE_BUCKET, Key=key)
            content = response['Body'].read().decode('utf-8')
            raw_data = json.loads(content)
            
            # Normalize data
            normalized = normalize_yahoo_data(raw_data, ticker)
            print(f"  Normalized {len(normalized)} price records")
            
            # Calculate technical indicators
            if normalized:
                normalized = calculate_technical_indicators(normalized)
            
            # Generate summary
            summary = generate_summary_stats(normalized, ticker)
            if summary:
                all_summaries.append(summary)
            
            # Write normalized data
            output_key = f"market_data/{ticker}/prices_normalized.json"
            output_data = {
                'ticker': ticker,
                'record_count': len(normalized),
                'processed_at': datetime.now().isoformat(),
                'summary': summary,
                'prices': normalized
            }
            
            s3_client.put_object(
                Bucket=TARGET_BUCKET,
                Key=output_key,
                Body=json.dumps(output_data, indent=2),
                ContentType='application/json'
            )
            
            print(f"  Written to s3://{TARGET_BUCKET}/{output_key}")
            files_processed += 1
            
        except Exception as e:
            print(f"  Error processing {key}: {str(e)}")
            files_failed += 1

# Write consolidated summary
if all_summaries:
    summary_key = "market_data/_summary.json"
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key=summary_key,
        Body=json.dumps({
            'tickers_processed': len(all_summaries),
            'generated_at': datetime.now().isoformat(),
            'summaries': all_summaries
        }, indent=2),
        ContentType='application/json'
    )
    print(f"Written market summary to s3://{TARGET_BUCKET}/{summary_key}")

print(f"\nProcessing complete:")
print(f"  Files processed: {files_processed}")
print(f"  Files failed: {files_failed}")

job.commit()
print("Job completed successfully!")
