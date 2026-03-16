"""
FinSight AI - Glue Python Shell Job: Process SEC Filings
Transforms raw SEC filings (10-K, 10-Q) into chunked documents ready for embedding.

Job Type: Python Shell (0.0625 DPU - ~$0.01/run)
"""

import sys
import json
import boto3
import re
from datetime import datetime

# -----------------------------------------------------------------------------
# Get Job Parameters
# -----------------------------------------------------------------------------
# Python Shell jobs receive arguments differently
args = {}
for i, arg in enumerate(sys.argv):
    if arg.startswith('--'):
        key = arg[2:]
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
            args[key] = sys.argv[i + 1]

SOURCE_BUCKET = args.get('source_bucket', 'finsight-ai-raw-617297630012')
TARGET_BUCKET = args.get('target_bucket', 'finsight-ai-processed-617297630012')
ACCOUNT_ID = args.get('account_id', '617297630012')

print(f"Starting SEC Filings ETL Job (Python Shell)")
print(f"Source: s3://{SOURCE_BUCKET}/sec_filings/")
print(f"Target: s3://{TARGET_BUCKET}/sec_filings/")

# -----------------------------------------------------------------------------
# Chunking Configuration
# -----------------------------------------------------------------------------
CHUNK_SIZE = 500       # Words per chunk
CHUNK_OVERLAP = 50     # Overlapping words between chunks

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks for RAG embedding."""
    if not text or not isinstance(text, str):
        return []
    
    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = start + chunk_size
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        
        if start >= len(words) - overlap:
            break
    
    return chunks

def extract_sections(filing_content):
    """Extract key sections from SEC filing content."""
    sections = []
    
    if isinstance(filing_content, dict):
        for key, value in filing_content.items():
            if isinstance(value, str) and len(value) > 100:
                sections.append({'section_name': key, 'content': value})
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str) and len(sub_value) > 100:
                        sections.append({
                            'section_name': f"{key}/{sub_key}",
                            'content': sub_value
                        })
    elif isinstance(filing_content, str):
        sections.append({'section_name': 'full_document', 'content': filing_content})
    
    return sections

def process_filing(filing_data):
    """Process a single SEC filing into chunks."""
    try:
        if isinstance(filing_data, str):
            filing = json.loads(filing_data)
        else:
            filing = filing_data
        
        # Extract metadata
        ticker = filing.get('ticker', 'UNKNOWN')
        filing_type = filing.get('filing_type', filing.get('doc_type', '10-K'))
        filing_date = filing.get('filing_date', filing.get('date', datetime.now().isoformat()))
        cik = filing.get('cik', '')
        company_name = filing.get('company_name', filing.get('company', ticker))
        
        # Get content
        content = filing.get('content', filing.get('text', filing.get('body', '')))
        sections = extract_sections(content) if content else extract_sections(filing)
        
        chunks = []
        chunk_id = 0
        
        for section in sections:
            section_chunks = chunk_text(section['content'])
            
            for chunk_text_content in section_chunks:
                chunks.append({
                    'chunk_id': f"{ticker}_{filing_type}_{chunk_id}",
                    'ticker': ticker,
                    'company_name': company_name,
                    'filing_type': filing_type,
                    'filing_date': filing_date,
                    'cik': cik,
                    'section': section['section_name'],
                    'content': chunk_text_content,
                    'word_count': len(chunk_text_content.split()),
                    'processed_at': datetime.now().isoformat(),
                    'source': f"sec_filings/{ticker}/{filing_type}.json"
                })
                chunk_id += 1
        
        return chunks
    
    except Exception as e:
        print(f"Error processing filing: {str(e)}")
        return []

# -----------------------------------------------------------------------------
# Main ETL Logic
# -----------------------------------------------------------------------------
s3_client = boto3.client('s3')

# List all files in sec_filings prefix
paginator = s3_client.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=SOURCE_BUCKET, Prefix='sec_filings/')

all_chunks = []
files_processed = 0
files_failed = 0

for page in pages:
    for obj in page.get('Contents', []):
        key = obj['Key']
        
        if not key.endswith('.json'):
            continue
        
        try:
            print(f"Processing: {key}")
            
            response = s3_client.get_object(Bucket=SOURCE_BUCKET, Key=key)
            content = response['Body'].read().decode('utf-8')
            filing_data = json.loads(content)
            
            chunks = process_filing(filing_data)
            all_chunks.extend(chunks)
            
            files_processed += 1
            print(f"  Generated {len(chunks)} chunks")
            
        except Exception as e:
            print(f"  Error processing {key}: {str(e)}")
            files_failed += 1

print(f"\nProcessing complete:")
print(f"  Files processed: {files_processed}")
print(f"  Files failed: {files_failed}")
print(f"  Total chunks generated: {len(all_chunks)}")

# Write chunks to processed bucket
if all_chunks:
    # Group chunks by ticker
    chunks_by_ticker = {}
    for chunk in all_chunks:
        ticker = chunk['ticker']
        if ticker not in chunks_by_ticker:
            chunks_by_ticker[ticker] = []
        chunks_by_ticker[ticker].append(chunk)
    
    # Write each ticker's chunks
    for ticker, ticker_chunks in chunks_by_ticker.items():
        output_key = f"sec_filings/{ticker}/chunks.json"
        output_data = {
            'ticker': ticker,
            'chunk_count': len(ticker_chunks),
            'processed_at': datetime.now().isoformat(),
            'chunks': ticker_chunks
        }
        
        s3_client.put_object(
            Bucket=TARGET_BUCKET,
            Key=output_key,
            Body=json.dumps(output_data, indent=2),
            ContentType='application/json'
        )
        print(f"Written {len(ticker_chunks)} chunks to s3://{TARGET_BUCKET}/{output_key}")

    # Consolidated file
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key="sec_filings/_all_chunks.json",
        Body=json.dumps(all_chunks, indent=2),
        ContentType='application/json'
    )
    print(f"Written consolidated chunks to s3://{TARGET_BUCKET}/sec_filings/_all_chunks.json")

print("Job completed successfully!")
