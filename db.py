"""
Database: transcript analyses + policy chunk embeddings (pgvector).

Configure via DATABASE_URL or POSTGRES_* (host, port, db, user, password).
Policy table needs `CREATE EXTENSION vector` once — see SETUP_DB.md.
"""
__all__ = [
    "store_transcript_analyses",
    "get_transcript_analyses",
    "store_policy_chunk_embeddings",
    "search_similar_policy_chunks",
]

# OpenAI text-embedding-3-small / ada-002
POLICY_EMBEDDING_DIMENSIONS = 1536
POLICY_SOURCE_DOCX = "policy_docx"
POLICY_SOURCE_TXT = "policy_txt"

import json
import os
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# Config (not exported)
# -----------------------------------------------------------------------------

def _get_connection_params():
    if os.environ.get("DATABASE_URL"):
        return {"conninfo": os.environ["DATABASE_URL"]}
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "customer_support"),
        "user": os.environ.get("POSTGRES_USER", "prachi"),
        "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
    }


@contextmanager
def _connection():
    import psycopg2
    params = _get_connection_params()
    if "conninfo" in params:
        conn = psycopg2.connect(params["conninfo"])
    else:
        conn = psycopg2.connect(**params)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transcript_analyses (
                id SERIAL PRIMARY KEY,
                transcript_id TEXT NOT NULL,
                issues_identified JSONB NOT NULL DEFAULT '[]',
                issue_identification_time DOUBLE PRECISION NOT NULL,
                summary_of_issue TEXT NOT NULL,
                issue_identified_by_chatbot BOOLEAN NOT NULL,
                issue_identified_by_human_agent BOOLEAN NOT NULL,
                resolution_stage TEXT NOT NULL,
                time_spent_on_issue DOUBLE PRECISION NOT NULL,
                bottleneck_category TEXT NOT NULL,
                user_feedback TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)


def _ensure_policy_chunks_table(conn):
    """
    Policy RAG chunks. Requires pgvector installed on the server and extension enabled.
    """
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            raise RuntimeError(
                "Enable pgvector on this database first:\n"
                "  brew install pgvector\n"
                "  psql -d customer_support -c 'CREATE EXTENSION vector;'\n"
                f"(Original error: {e})"
            ) from e
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS policy_chunks (
                id SERIAL PRIMARY KEY,
                embedding vector({POLICY_EMBEDDING_DIMENSIONS}) NOT NULL,
                source TEXT NOT NULL,
                document_name TEXT NOT NULL,
                section_heading TEXT NOT NULL DEFAULT '',
                chunk_index INT NOT NULL,
                uploaded_at TIMESTAMPTZ NOT NULL,
                content TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS policy_chunks_document_idx
            ON policy_chunks (document_name, chunk_index);
            """
        )


def _vector_param(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


# -----------------------------------------------------------------------------
# Public API: use these from any node (transcript_analysis.py or other files)
# -----------------------------------------------------------------------------

def get_transcript_analyses(
    *,
    transcript_ids: list[str] | None = None,
    resolution_stage: str | None = None,
    bottleneck_category: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    Query stored transcript analyses from the DB. Optional filters.
    Returns list of dicts with keys: transcript_id, issues_identified, summary_of_issue,
    resolution_stage, bottleneck_category, user_feedback, time_spent_on_issue, etc.
    """
    with _connection() as conn:
        _ensure_table(conn)
        with conn.cursor() as cur:
            conditions = []
            params = []
            if transcript_ids:
                conditions.append("transcript_id = ANY(%s)")
                params.append(transcript_ids)
            if resolution_stage:
                conditions.append("resolution_stage = %s")
                params.append(resolution_stage)
            if bottleneck_category:
                conditions.append("bottleneck_category = %s")
                params.append(bottleneck_category)
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""
            cur.execute(
                f"""
                SELECT transcript_id, issues_identified, issue_identification_time,
                       summary_of_issue, issue_identified_by_chatbot,
                       issue_identified_by_human_agent, resolution_stage,
                       time_spent_on_issue, bottleneck_category, user_feedback, created_at
                FROM transcript_analyses
                {where}
                ORDER BY created_at DESC
                {limit_clause}
                """,
                params if params else (),
            )
            columns = [d.name for d in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def store_transcript_analyses(analyses: list[dict]) -> None:
    """
    Insert transcript analysis records into the local Postgres DB.
    Each item in `analyses` must be a dict with keys matching TranscriptAnalysis
    (e.g. from TranscriptAnalysis.model_dump()).
    """
    if not analyses:
        return
    with _connection() as conn:
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO transcript_analyses (
                    transcript_id, issues_identified, issue_identification_time,
                    summary_of_issue, issue_identified_by_chatbot,
                    issue_identified_by_human_agent, resolution_stage,
                    time_spent_on_issue, bottleneck_category, user_feedback
                ) VALUES (
                    %(transcriptId)s, %(issuesIdentified)s::jsonb, %(issueIdentificationTime)s,
                    %(summary_of_issue)s, %(issueIdentifiedByChatbot)s,
                    %(issueIdentifiedByHumanAgent)s, %(resolution_stage)s,
                    %(time_spent_on_issue)s, %(bottleneck_category)s, %(user_feedback)s
                )
                """,
                [
                    {
                        "transcriptId": a["transcriptId"],
                        "issuesIdentified": json.dumps(a.get("issuesIdentified", [])),
                        "issueIdentificationTime": float(a.get("issueIdentificationTime", 0)),
                        "summary_of_issue": a.get("summary_of_issue", ""),
                        "issueIdentifiedByChatbot": bool(a.get("issueIdentifiedByChatbot", False)),
                        "issueIdentifiedByHumanAgent": bool(a.get("issueIdentifiedByHumanAgent", False)),
                        "resolution_stage": a.get("resolution_stage", ""),
                        "time_spent_on_issue": float(a.get("time_spent_on_issue", 0)),
                        "bottleneck_category": a.get("bottleneck_category", ""),
                        "user_feedback": a.get("user_feedback", ""),
                    }
                    for a in analyses
                ],
            )


def store_policy_chunk_embeddings(
    rows: list[dict],
    embeddings: list[list[float]],
    *,
    source: str = POLICY_SOURCE_TXT,
) -> None:
    """
    Replace existing chunks for the same (source, document_name) then insert.
    Each row: content, document_name, section_heading, chunk_index, uploaded_at (datetime).
    """
    if not rows or len(rows) != len(embeddings):
        return
    if any(len(e) != POLICY_EMBEDDING_DIMENSIONS for e in embeddings):
        raise ValueError(
            f"Embeddings must have dimension {POLICY_EMBEDDING_DIMENSIONS} "
            "(use text-embedding-3-small or matching model)."
        )
    doc_names = list({r["document_name"] for r in rows})
    with _connection() as conn:
        _ensure_policy_chunks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM policy_chunks WHERE source = %s AND document_name = ANY(%s)",
                (source, doc_names),
            )
            for row, emb in zip(rows, embeddings):
                cur.execute(
                    """
                    INSERT INTO policy_chunks (
                        embedding, source, document_name, section_heading,
                        chunk_index, uploaded_at, content
                    ) VALUES (%s::vector, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        _vector_param(emb),
                        source,
                        row["document_name"],
                        row.get("section_heading") or "",
                        int(row["chunk_index"]),
                        row["uploaded_at"],
                        row["content"],
                    ),
                )


def search_similar_policy_chunks(
    query_embedding: list[float],
    *,
    limit: int = 8,
    source: str | None = POLICY_SOURCE_TXT,
) -> list[dict]:
    """
    Cosine distance via pgvector (<=>). Returns chunks with metadata for citations.
    """
    if len(query_embedding) != POLICY_EMBEDDING_DIMENSIONS:
        raise ValueError(f"Query embedding dim must be {POLICY_EMBEDDING_DIMENSIONS}")
    with _connection() as conn:
        _ensure_policy_chunks_table(conn)
        with conn.cursor() as cur:
            if source:
                cur.execute(
                    """
                    SELECT document_name, section_heading, chunk_index, content,
                           uploaded_at, source,
                           (embedding <=> %s::vector) AS distance
                    FROM policy_chunks
                    WHERE source = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (_vector_param(query_embedding), source, _vector_param(query_embedding), limit),
                )
            else:
                cur.execute(
                    """
                    SELECT document_name, section_heading, chunk_index, content,
                           uploaded_at, source,
                           (embedding <=> %s::vector) AS distance
                    FROM policy_chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (_vector_param(query_embedding), _vector_param(query_embedding), limit),
                )
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
