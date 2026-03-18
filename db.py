"""
Database configuration and functions for storing/querying transcript analyses.
Any node (in transcript_analysis.py or another file) can import from here.

Configure via environment: DATABASE_URL or POSTGRES_* vars (host, port, db, user, password).
"""
__all__ = ["store_transcript_analyses", "get_transcript_analyses"]

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
