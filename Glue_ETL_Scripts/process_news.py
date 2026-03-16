"""
FinSight AI - Glue ETL Job: Process News Data
Transforms raw news articles into sentiment-ready format for RAG embedding.

Input:  s3://finsight-ai-raw-{account_id}/news/{ticker}/articles.json
Output: s3://finsight-ai-processed-{account_id}/news/{ticker}/articles_processed.json
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
# Text Processing Functions
# -----------------------------------------------------------------------------

# Simple keyword-based sentiment (for demo - use Bedrock/Comprehend in production)
POSITIVE_WORDS = {
    'growth', 'profit', 'gain', 'surge', 'rise', 'jump', 'soar', 'boost',
    'success', 'beat', 'exceed', 'strong', 'positive', 'upgrade', 'buy',
    'outperform', 'bullish', 'rally', 'record', 'high', 'innovation',
    'breakthrough', 'expansion', 'dividend', 'revenue', 'earnings'
}

NEGATIVE_WORDS = {
    'loss', 'decline', 'fall', 'drop', 'plunge', 'crash', 'weak', 'miss',
    'cut', 'downgrade', 'sell', 'underperform', 'bearish', 'concern',
    'risk', 'debt', 'lawsuit', 'investigation', 'recall', 'layoff',
    'bankruptcy', 'fraud', 'scandal', 'warning', 'slowdown', 'recession'
}

def clean_text(text):
    """
    Clean and normalize article text.
    """
    if not text or not isinstance(text, str):
        return ''
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s.,!?;:\'-]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_keywords(text, top_n=10):
    """
    Extract top keywords from text (simple TF approach).
    """
    if not text:
        return []
    
    # Common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'dare', 'ought', 'used', 'it', 'its', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'we', 'they', 'what', 'which', 'who', 'whom',
        'said', 'says', 'according', 'also', 'just', 'like', 'more', 'than'
    }
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = {}
    
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:top_n]]

def calculate_sentiment(text):
    """
    Calculate simple sentiment score based on keyword matching.
    Returns score from -1 (negative) to +1 (positive).
    
    Note: For production, use AWS Comprehend or Bedrock.
    """
    if not text:
        return {'score': 0, 'label': 'neutral', 'confidence': 0}
    
    words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    
    positive_count = len(words & POSITIVE_WORDS)
    negative_count = len(words & NEGATIVE_WORDS)
    total_sentiment_words = positive_count + negative_count
    
    if total_sentiment_words == 0:
        return {'score': 0, 'label': 'neutral', 'confidence': 0.5}
    
    score = (positive_count - negative_count) / total_sentiment_words
    
    # Determine label
    if score > 0.2:
        label = 'positive'
    elif score < -0.2:
        label = 'negative'
    else:
        label = 'neutral'
    
    # Confidence based on number of sentiment words found
    confidence = min(total_sentiment_words / 10, 1.0)
    
    return {
        'score': round(score, 3),
        'label': label,
        'confidence': round(confidence, 3),
        'positive_words': positive_count,
        'negative_words': negative_count
    }

def extract_entities(text):
    """
    Extract basic financial entities (tickers, numbers, dates).
    Note: For production, use AWS Comprehend or Bedrock.
    """
    entities = {
        'tickers': [],
        'money_values': [],
        'percentages': [],
        'dates': []
    }
    
    if not text:
        return entities
    
    # Stock tickers (basic pattern)
    tickers = re.findall(r'\b[A-Z]{2,5}\b(?=\s|$|,|\.)', text)
    common_words = {'CEO', 'CFO', 'IPO', 'SEC', 'NYSE', 'US', 'USA', 'AI', 'IT', 'THE', 'AND', 'FOR'}
    entities['tickers'] = list(set(t for t in tickers if t not in common_words))[:10]
    
    # Money values
    money = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|trillion))?', text, re.IGNORECASE)
    entities['money_values'] = money[:5]
    
    # Percentages
    percentages = re.findall(r'[\d.]+\s*%', text)
    entities['percentages'] = percentages[:5]
    
    return entities

def chunk_article(article, max_chunk_size=500):
    """
    Chunk article for embedding while preserving context.
    """
    content = article.get('content', '') or article.get('body', '') or article.get('text', '')
    content = clean_text(content)
    
    if not content:
        return []
    
    words = content.split()
    
    if len(words) <= max_chunk_size:
        return [content]
    
    chunks = []
    for i in range(0, len(words), max_chunk_size - 50):
        chunk = ' '.join(words[i:i + max_chunk_size])
        chunks.append(chunk)
    
    return chunks

def process_article(article, ticker):
    """
    Process a single news article.
    """
    # Extract and clean content
    title = clean_text(article.get('title', ''))
    content = clean_text(
        article.get('content', '') or 
        article.get('body', '') or 
        article.get('description', '') or
        article.get('text', '')
    )
    
    full_text = f"{title}. {content}"
    
    # Calculate sentiment
    sentiment = calculate_sentiment(full_text)
    
    # Extract entities and keywords
    entities = extract_entities(full_text)
    keywords = extract_keywords(full_text)
    
    # Chunk for embedding
    chunks = chunk_article(article)
    
    processed = {
        'article_id': article.get('id', hash(title) % 10**8),
        'ticker': ticker,
        'title': title,
        'source': article.get('source', {}).get('name', article.get('source', 'Unknown')),
        'author': article.get('author', 'Unknown'),
        'published_at': article.get('publishedAt', article.get('published_at', article.get('date', ''))),
        'url': article.get('url', ''),
        'content_length': len(content),
        'word_count': len(content.split()),
        'sentiment': sentiment,
        'keywords': keywords,
        'entities': entities,
        'chunks': chunks,
        'chunk_count': len(chunks),
        'processed_at': datetime.now().isoformat()
    }
    
    return processed

# -----------------------------------------------------------------------------
# Main ETL Logic
# -----------------------------------------------------------------------------
print(f"Starting News Data ETL Job")
print(f"Source: s3://{SOURCE_BUCKET}/news/")
print(f"Target: s3://{TARGET_BUCKET}/news/")

s3_client = boto3.client('s3')

# List all news files
paginator = s3_client.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=SOURCE_BUCKET, Prefix='news/')

all_articles = []
sentiment_summary = {
    'positive': 0,
    'negative': 0,
    'neutral': 0
}
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
            ticker = parts[1] if len(parts) > 1 else 'GENERAL'
            
            # Read file
            response = s3_client.get_object(Bucket=SOURCE_BUCKET, Key=key)
            content = response['Body'].read().decode('utf-8')
            raw_data = json.loads(content)
            
            # Handle different formats
            articles = []
            if isinstance(raw_data, list):
                articles = raw_data
            elif 'articles' in raw_data:
                articles = raw_data['articles']
            elif 'results' in raw_data:
                articles = raw_data['results']
            else:
                articles = [raw_data]
            
            # Process each article
            processed_articles = []
            for article in articles:
                processed = process_article(article, ticker)
                processed_articles.append(processed)
                sentiment_summary[processed['sentiment']['label']] += 1
            
            all_articles.extend(processed_articles)
            print(f"  Processed {len(processed_articles)} articles")
            
            # Write processed articles
            output_key = f"news/{ticker}/articles_processed.json"
            output_data = {
                'ticker': ticker,
                'article_count': len(processed_articles),
                'processed_at': datetime.now().isoformat(),
                'sentiment_breakdown': {
                    'positive': sum(1 for a in processed_articles if a['sentiment']['label'] == 'positive'),
                    'negative': sum(1 for a in processed_articles if a['sentiment']['label'] == 'negative'),
                    'neutral': sum(1 for a in processed_articles if a['sentiment']['label'] == 'neutral')
                },
                'articles': processed_articles
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

# Write consolidated summary for embedding
if all_articles:
    # Extract all chunks for embedding
    all_chunks = []
    for article in all_articles:
        for i, chunk in enumerate(article.get('chunks', [])):
            all_chunks.append({
                'chunk_id': f"{article['ticker']}_news_{article['article_id']}_{i}",
                'ticker': article['ticker'],
                'source_type': 'news',
                'title': article['title'],
                'source': article['source'],
                'published_at': article['published_at'],
                'sentiment': article['sentiment']['label'],
                'sentiment_score': article['sentiment']['score'],
                'content': chunk,
                'processed_at': article['processed_at']
            })
    
    # Write chunks for embedding pipeline
    chunks_key = "news/_all_chunks.json"
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key=chunks_key,
        Body=json.dumps(all_chunks, indent=2),
        ContentType='application/json'
    )
    print(f"Written {len(all_chunks)} news chunks to s3://{TARGET_BUCKET}/{chunks_key}")
    
    # Write summary
    summary_key = "news/_summary.json"
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key=summary_key,
        Body=json.dumps({
            'total_articles': len(all_articles),
            'total_chunks': len(all_chunks),
            'sentiment_summary': sentiment_summary,
            'processed_at': datetime.now().isoformat()
        }, indent=2),
        ContentType='application/json'
    )
    print(f"Written summary to s3://{TARGET_BUCKET}/{summary_key}")

print(f"\nProcessing complete:")
print(f"  Files processed: {files_processed}")
print(f"  Files failed: {files_failed}")
print(f"  Total articles: {len(all_articles)}")
print(f"  Sentiment breakdown: {sentiment_summary}")

job.commit()
print("Job completed successfully!")
