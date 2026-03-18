#!/usr/bin/env python3
"""
View transcript_analyses table in the local Postgres DB.
Run: python view_db.py [--limit N]
Uses same config as db.py (DATABASE_URL or POSTGRES_* env vars).
"""
import argparse
import json

from db import get_transcript_analyses


def main():
    p = argparse.ArgumentParser(description="View transcript analyses in the DB")
    p.add_argument("--limit", type=int, default=50, help="Max rows to show (default 50)")
    p.add_argument("--resolution", type=str, help="Filter by resolution_stage")
    p.add_argument("--bottleneck", type=str, help="Filter by bottleneck_category")
    args = p.parse_args()
    try:
        rows = get_transcript_analyses(
            resolution_stage=args.resolution or None,
            bottleneck_category=args.bottleneck or None,
            limit=args.limit,
        )
    except Exception as e:
        print("Could not connect to the database.")
        print(f"  Error: {e}")
        print("\nEnsure Postgres is running and .env has POSTGRES_* or DATABASE_URL set.")
        print("  Example: createdb customer_support && set POSTGRES_PASSWORD in .env")
        return
    print(f"Found {len(rows)} row(s)\n")
    for i, r in enumerate(rows, 1):
        issues = r.get("issues_identified")
        if isinstance(issues, str):
            try:
                issues = json.loads(issues)
            except Exception:
                pass
        print(f"--- Row {i} ---")
        # datetime from Postgres is not JSON-serializable by default
        print(json.dumps(r, indent=4, default=str))
        print()
        print("-" * 100)


if __name__ == "__main__":
    main()
