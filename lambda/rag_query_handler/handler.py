"""
rag_query_handler/handler.py
Handles RAG queries: embeds the question, retrieves similar chunks
from pgvector, then calls Bedrock Claude to generate a grounded answer.
Invoked by API Gateway (POST /query).
"""

import json
import os
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor

secrets = boto3.client("secretsmanager", region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))
bedrock = boto3.client("bedrock-runtime",  region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))

# Cache DB connection across warm invocations
_db_conn = None


# ─── Database ────────────────────────────────────────────────────────────────

def get_db_conn():
    global _db_conn
    if _db_conn is None or _db_conn.closed:
        secret = json.loads(
            secrets.get_secret_value(SecretId=os.environ["DB_SECRET_ID"])["SecretString"]
        )
        _db_conn = psycopg2.connect(
            host=secret["host"],
            port=int(secret.get("port", 5432)),
            dbname=secret.get("dbname", "postgres"),
            user=secret["username"],
            password=secret["password"],
            connect_timeout=10,
        )
    return _db_conn


# ─── Embedding ───────────────────────────────────────────────────────────────

def embed_query(text: str) -> list[float]:
    """Embed the user query using Amazon Titan Embed v2."""
    resp = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text[:8000]}),
    )
    return json.loads(resp["body"].read())["embedding"]


# ─── Vector Search ───────────────────────────────────────────────────────────

def retrieve_chunks(query_vec: list[float], top_k: int = 5, ticker: str = None) -> list[dict]:
    """Retrieve top-k most similar document chunks from pgvector."""
    conn = get_db_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if ticker:
            cur.execute("""
                SELECT
                    chunk_text,
                    source,
                    doc_type,
                    ticker,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                WHERE ticker = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_vec, ticker.upper(), query_vec, top_k))
        else:
            cur.execute("""
                SELECT
                    chunk_text,
                    source,
                    doc_type,
                    ticker,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_vec, query_vec, top_k))

        return [dict(row) for row in cur.fetchall()]


# ─── LLM Generation ──────────────────────────────────────────────────────────

def generate_answer(query: str, chunks: list[dict]) -> str:
    """Generate a grounded financial answer using Claude via Bedrock."""
    context = "\n\n".join(
        f"[Source: {c['source']} | Type: {c.get('doc_type','?')} | Ticker: {c.get('ticker','?')} | Score: {c['similarity']:.3f}]\n{c['chunk_text']}"
        for c in chunks
    )

    system_prompt = """You are FinSight AI, an expert financial analyst assistant.
Answer questions using ONLY the context provided. Be precise and concise.
Always cite your sources using the [Source: ...] tags from the context.
If the context doesn't contain enough information, say so clearly — do not hallucinate."""

    prompt = f"""Context from financial documents:

{context}

---

Question: {query}

Provide a clear, accurate answer with source citations."""

    resp = bedrock.invoke_model(
        modelId=os.environ.get("LLM_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"),
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens":        1024,
            "system":            system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }),
    )
    return json.loads(resp["body"].read())["content"][0]["text"]


# ─── Main Handler ────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    # Parse request body (API Gateway or direct invoke)
    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        elif isinstance(event.get("body"), dict):
            body = event["body"]
        else:
            body = event
    except (json.JSONDecodeError, AttributeError):
        body = event

    query  = body.get("query", "").strip()
    top_k  = int(body.get("top_k", os.environ.get("TOP_K", 5)))
    ticker = body.get("ticker")   # optional filter by ticker

    if not query:
        return {
            "statusCode": 400,
            "headers":    {"Content-Type": "application/json"},
            "body":       json.dumps({"error": "query field is required"}),
        }

    print(f"[INFO] RAG query: '{query}' | ticker={ticker} | top_k={top_k}")

    try:
        # 1. Embed the query
        query_vec = embed_query(query)

        # 2. Retrieve relevant chunks
        chunks = retrieve_chunks(query_vec, top_k=top_k, ticker=ticker)
        print(f"[INFO] Retrieved {len(chunks)} chunks")

        if not chunks:
            return {
                "statusCode": 200,
                "headers":    {"Content-Type": "application/json"},
                "body":       json.dumps({
                    "answer":  "No relevant financial data found for your query.",
                    "sources": [],
                    "chunks":  0,
                }),
            }

        # 3. Generate grounded answer
        answer = generate_answer(query, chunks)

        return {
            "statusCode": 200,
            "headers":    {
                "Content-Type":                "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "answer":  answer,
                "sources": list({c["source"] for c in chunks}),
                "chunks":  len(chunks),
                "top_results": [
                    {
                        "source":     c["source"],
                        "ticker":     c.get("ticker"),
                        "doc_type":   c.get("doc_type"),
                        "similarity": round(c["similarity"], 4),
                    }
                    for c in chunks
                ],
            }),
        }

    except psycopg2.Error as e:
        print(f"[ERROR] DB error: {e}")
        return {
            "statusCode": 503,
            "body":       json.dumps({"error": "Database error", "detail": str(e)}),
        }
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return {
            "statusCode": 500,
            "body":       json.dumps({"error": "Internal server error", "detail": str(e)}),
        }
