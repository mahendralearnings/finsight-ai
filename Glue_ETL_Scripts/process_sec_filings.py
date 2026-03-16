"""
FinSight AI - Glue ETL Job: Process SEC Filings
Transforms raw SEC filings (10-K, 10-Q) into chunked documents ready for embedding.

Input:  s3://finsight-ai-raw-{account_id}/sec_filings/{ticker}/{filing_type}.json
Output: s3://finsight-ai-processed-{account_id}/sec_filings/{ticker}/{filing_type}_chunks.json
"""

import sys
import json
import boto3
import re
from datetime import datetime
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import udf, explode, col, lit
from pyspark.sql.types import ArrayType, StructType, StructField, StringType, IntegerType

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
# Chunking Configuration
# -----------------------------------------------------------------------------
CHUNK_SIZE = 500       # Words per chunk
CHUNK_OVERLAP = 50     # Overlapping words between chunks

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split text into overlapping chunks for RAG embedding.
    
    Args:
        text: Input text to chunk
        chunk_size: Number of words per chunk
        overlap: Number of overlapping words between chunks
    
    Returns:
        List of text chunks
    """
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
        
        # Prevent infinite loop
        if start >= len(words) - overlap:
            break
    
    return chunks

def extract_sections(filing_content):
    """
    Extract key sections from SEC filing content.
    Handles both raw text and structured JSON.
    """
    sections = []
    
    if isinstance(filing_content, dict):
        # Structured filing
        for key, value in filing_content.items():
            if isinstance(value, str) and len(value) > 100:
                sections.append({
                    'section_name': key,
                    'content': value
                })
            elif isinstance(value, dict):
                # Nested sections
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str) and len(sub_value) > 100:
                        sections.append({
                            'section_name': f"{key}/{sub_key}",
                            'content': sub_value
                        })
    elif isinstance(filing_content, str):
        # Raw text - treat as single section
        sections.append({
            'section_name': 'full_document',
            'content': filing_content
        })
    
    return sections

def process_filing(filing_json):
    """
    Process a single SEC filing into chunks.
    
    Returns list of chunk dictionaries ready for embedding.
    """
    try:
        if isinstance(filing_json, str):
            filing = json.loads(filing_json)
        else:
            filing = filing_json
        
        # Extract metadata
        ticker = filing.get('ticker', 'UNKNOWN')
        filing_type = filing.get('filing_type', filing.get('doc_type', '10-K'))
        filing_date = filing.get('filing_date', filing.get('date', datetime.now().isoformat()))
        cik = filing.get('cik', '')
        company_name = filing.get('company_name', filing.get('company', ticker))
        
        # Get content
        content = filing.get('content', filing.get('text', filing.get('body', '')))
        
        # Extract sections and chunk
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
print(f"Starting SEC Filings ETL Job")
print(f"Source: s3://{SOURCE_BUCKET}/sec_filings/")
print(f"Target: s3://{TARGET_BUCKET}/sec_filings/")

# Read raw SEC filings from S3
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
        
        # Skip non-JSON files
        if not key.endswith('.json'):
            continue
        
        try:
            print(f"Processing: {key}")
            
            # Read file
            response = s3_client.get_object(Bucket=SOURCE_BUCKET, Key=key)
            content = response['Body'].read().decode('utf-8')
            filing_data = json.loads(content)
            
            # Process filing into chunks
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
    
    # Write each ticker's chunks to S3
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

    # Also write a consolidated file for easy embedding
    consolidated_key = "sec_filings/_all_chunks.json"
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key=consolidated_key,
        Body=json.dumps(all_chunks, indent=2),
        ContentType='application/json'
    )
    print(f"Written consolidated chunks to s3://{TARGET_BUCKET}/{consolidated_key}")

job.commit()
print("Job completed successfully!")
