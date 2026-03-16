"""
embed_documents/handler.py
Reads processed documents from S3, generates Bedrock embeddings,
and stores them in pgvector (RDS). Self-initializes DB schema on first run.
Triggered by S3 event on processed bucket, or manually.
"""

import json
import os
import boto3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timezone

s3      = boto3.client("s3")
secrets = boto3.client("secretsmanager", region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))
bedrock = boto3.client("bedrock-runtime",  region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))


# ─── Database ────────────────────────────────────────────────────────────────

def get_db_conn():
    """Retrieve RDS credentials from Secrets Manager and connect."""
    secret = json.loads(
        secrets.get_secret_value(SecretId=os.environ["DB_SECRET_ID"])["SecretString"]
    )
    return psycopg2.connect(
        host=secret["host"],
        port=int(secret.get("port", 5432)),
        dbname=secret.get("dbname", "postgres"),
        user=secret["username"],
        password=secret["password"],
        connect_timeout=10,
    )


def init_db(conn) -> None:
    """
    Self-initializes pgvector extension and document_chunks table.
    DROP TABLE ensures clean schema on dimension change.
    """
    with conn.cursor() as cur:
        print("[INFO] Initializing pgvector extension and schema...")

        # Install pgvector
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Drop and recreate to fix any dimension mismatches
        cur.execute("DROP TABLE IF EXISTS document_chunks;")

        # Main embeddings table — Titan Embed V2 = 1024 dimensions
        cur.execute("""
            CREATE TABLE document_chunks (
                id          SERIAL PRIMARY KEY,
                chunk_text  TEXT        NOT NULL,
                embedding   vector(1024),
                source      TEXT,
                doc_type    TEXT,
                ticker      TEXT,
                metadata    JSONB       DEFAULT '{}',
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # HNSW index for fast cosine similarity search
        cur.execute("""
            CREATE INDEX idx_embedding_hnsw
            ON document_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

        # Index for filtering by ticker
        cur.execute("""
            CREATE INDEX idx_ticker
            ON document_chunks (ticker);
        """)

        conn.commit()
        print("[INFO] Schema ready.")


# ─── Text Chunking ───────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words  = text.split()
    chunks = []
    step   = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# ─── Bedrock Embedding ───────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """Generate embedding vector using Amazon Titan Embed v2 (1024 dims)."""
    resp = bedrock.invoke_model(
        modelId=os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0"),
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text[:8000]}),
    )
    return json.loads(resp["body"].read())["embedding"]


# ─── Main Handler ────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    print(f"[INFO] embed_documents invoked — event: {json.dumps(event)[:300]}")

    # Support both S3 event trigger and manual invocation
    if "Records" in event:
        records = [
            {
                "bucket": r["s3"]["bucket"]["name"],
                "key":    r["s3"]["object"]["key"],
            }
            for r in event["Records"]
            if r.get("eventSource") == "aws:s3"
        ]
    elif "bucket" in event and "key" in event:
        records = [{"bucket": event["bucket"], "key": event["key"]}]
    else:
        return {"statusCode": 400, "body": "No S3 records found in event"}

    conn = get_db_conn()
    try:
        # Self-init schema (drops and recreates cleanly)
        init_db(conn)

        total_chunks = 0

        for record in records:
            bucket = record["bucket"]
            key    = record["key"]

            print(f"[INFO] Processing s3://{bucket}/{key}")

            obj     = s3.get_object(Bucket=bucket, Key=key)
            content = obj["Body"].read().decode("utf-8")

            # Try to parse as JSON (structured ingest output)
            try:
                parsed   = json.loads(content)
                text     = parsed.get("text") or parsed.get("content") or json.dumps(parsed)
                ticker   = parsed.get("ticker", "UNKNOWN")
                doc_type = parsed.get("form") or parsed.get("type", "unknown")
            except json.JSONDecodeError:
                text     = content
                ticker   = "UNKNOWN"
                doc_type = "raw"

            chunks = chunk_text(text)
            print(f"[INFO] {key} → {len(chunks)} chunks")

            rows = []
            for chunk in chunks:
                try:
                    vector = embed_text(chunk)
                    rows.append((
                        chunk,
                        vector,
                        key,
                        doc_type,
                        ticker,
                        json.dumps({"bucket": bucket, "key": key}),
                    ))
                except Exception as e:
                    print(f"[WARN] Embedding failed for chunk: {e}")
                    continue

            if rows:
                with conn.cursor() as cur:
                    execute_values(cur, """
                        INSERT INTO document_chunks
                            (chunk_text, embedding, source, doc_type, ticker, metadata)
                        VALUES %s
                    """, rows)
                conn.commit()
                total_chunks += len(rows)
                print(f"[INFO] Stored {len(rows)} embeddings for {key}")

    finally:
        conn.close()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":         "Embedding complete",
            "files_processed": len(records),
            "chunks_stored":   total_chunks,
            "timestamp":       datetime.now(timezone.utc).isoformat(),
        })
    }