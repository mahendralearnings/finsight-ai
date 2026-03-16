"""
FinSight AI - Glue Python Shell Job: Process News Data
Transforms raw news articles into sentiment-ready format for RAG embedding.

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
args = {}
for i, arg in enumerate(sys.argv):
    if arg.startswith('--'):
        key = arg[2:]
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
            args[key] = sys.argv[i + 1]

SOURCE_BUCKET = args.get('source_bucket', 'finsight-ai-raw-617297630012')
TARGET_BUCKET = args.get('target_bucket', 'finsight-ai-processed-617297630012')

print(f"Starting News Data ETL Job (Python Shell)")
print(f"Source: s3://{SOURCE_BUCKET}/news/")
print(f"Target: s3://{TARGET_BUCKET}/news/")

# -----------------------------------------------------------------------------
# Sentiment Keywords
# -----------------------------------------------------------------------------
POSITIVE_WORDS = {
    'growth', 'profit', 'gain', 'surge', 'rise', 'jump', 'soar', 'boost',
    'success', 'beat', 'exceed', 'strong', 'positive', 'upgrade', 'buy',
    'outperform', 'bullish', 'rally', 'record', 'high', 'innovation'
}

NEGATIVE_WORDS = {
    'loss', 'decline', 'fall', 'drop', 'plunge', 'crash', 'weak', 'miss',
    'cut', 'downgrade', 'sell', 'underperform', 'bearish', 'concern',
    'risk', 'debt', 'lawsuit', 'investigation', 'recall', 'layoff'
}

# -----------------------------------------------------------------------------
# Processing Functions
# -----------------------------------------------------------------------------
def clean_text(text):
    """Clean and normalize text."""
    if not text or not isinstance(text, str):
        return ''
    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML
    text = re.sub(r'http[s]?://\S+', '', text)  # Remove URLs
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_sentiment(text):
    """Calculate simple sentiment score."""
    if not text:
        return {'score': 0, 'label': 'neutral', 'confidence': 0}
    
    words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
    
    positive_count = len(words & POSITIVE_WORDS)
    negative_count = len(words & NEGATIVE_WORDS)
    total = positive_count + negative_count
    
    if total == 0:
        return {'score': 0, 'label': 'neutral', 'confidence': 0.5}
    
    score = (positive_count - negative_count) / total
    
    if score > 0.2:
        label = 'positive'
    elif score < -0.2:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {
        'score': round(score, 3),
        'label': label,
        'confidence': round(min(total / 10, 1.0), 3)
    }

def extract_keywords(text, top_n=10):
    """Extract top keywords from text."""
    if not text:
        return []
    
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'said', 'says', 'according', 'also', 'just', 'like', 'more', 'than'
    }
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = {}
    
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:top_n]]

def chunk_article(content, max_chunk_size=500):
    """Chunk article for embedding."""
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
    """Process a single news article."""
    title = clean_text(article.get('title', ''))
    content = clean_text(
        article.get('content', '') or 
        article.get('body', '') or 
        article.get('description', '') or
        article.get('text', '')
    )
    
    full_text = f"{title}. {content}"
    sentiment = calculate_sentiment(full_text)
    keywords = extract_keywords(full_text)
    chunks = chunk_article(content)
    
    return {
        'article_id': article.get('id', hash(title) % 10**8),
        'ticker': ticker,
        'title': title,
        'source': article.get('source', {}).get('name', article.get('source', 'Unknown')),
        'author': article.get('author', 'Unknown'),
        'published_at': article.get('publishedAt', article.get('published_at', article.get('date', ''))),
        'url': article.get('url', ''),
        'word_count': len(content.split()),
        'sentiment': sentiment,
        'keywords': keywords,
        'chunks': chunks,
        'chunk_count': len(chunks),
        'processed_at': datetime.now().isoformat()
    }

# -----------------------------------------------------------------------------
# Main ETL Logic
# -----------------------------------------------------------------------------
s3_client = boto3.client('s3')

paginator = s3_client.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=SOURCE_BUCKET, Prefix='news/')

all_articles = []
sentiment_summary = {'positive': 0, 'negative': 0, 'neutral': 0}
files_processed = 0
files_failed = 0

for page in pages:
    for obj in page.get('Contents', []):
        key = obj['Key']
        
        if not key.endswith('.json'):
            continue
        
        try:
            print(f"Processing: {key}")
            
            parts = key.split('/')
            ticker = parts[1] if len(parts) > 1 else 'GENERAL'
            
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
            s3_client.put_object(
                Bucket=TARGET_BUCKET,
                Key=output_key,
                Body=json.dumps({
                    'ticker': ticker,
                    'article_count': len(processed_articles),
                    'processed_at': datetime.now().isoformat(),
                    'articles': processed_articles
                }, indent=2),
                ContentType='application/json'
            )
            
            print(f"  Written to s3://{TARGET_BUCKET}/{output_key}")
            files_processed += 1
            
        except Exception as e:
            print(f"  Error: {str(e)}")
            files_failed += 1

# Write chunks for embedding
if all_articles:
    all_chunks = []
    for article in all_articles:
        for i, chunk in enumerate(article.get('chunks', [])):
            all_chunks.append({
                'chunk_id': f"{article['ticker']}_news_{article['article_id']}_{i}",
                'ticker': article['ticker'],
                'source_type': 'news',
                'title': article['title'],
                'sentiment': article['sentiment']['label'],
                'sentiment_score': article['sentiment']['score'],
                'content': chunk,
                'processed_at': article['processed_at']
            })
    
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key="news/_all_chunks.json",
        Body=json.dumps(all_chunks, indent=2),
        ContentType='application/json'
    )
    print(f"Written {len(all_chunks)} news chunks")
    
    s3_client.put_object(
        Bucket=TARGET_BUCKET,
        Key="news/_summary.json",
        Body=json.dumps({
            'total_articles': len(all_articles),
            'total_chunks': len(all_chunks),
            'sentiment_summary': sentiment_summary,
            'processed_at': datetime.now().isoformat()
        }, indent=2),
        ContentType='application/json'
    )

print(f"\nProcessing complete:")
print(f"  Files processed: {files_processed}")
print(f"  Files failed: {files_failed}")
print(f"  Total articles: {len(all_articles)}")
print(f"  Sentiment: {sentiment_summary}")
print("Job completed successfully!")
