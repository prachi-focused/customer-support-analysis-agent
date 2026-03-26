"""Report generation node for the LangGraph workflow."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from generate_report_body import generate_report_body
from report_policy_reasoning import generate_policy_reasoning_markdown


def _ops_and_failure(state: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_o = state.get("operations_metrics") or {}
    raw_f = state.get("failure_metrics") or {}
    return (
        raw_o if isinstance(raw_o, dict) else {},
        raw_f if isinstance(raw_f, dict) else {},
    )


def _assemble_full_report(report_body: str, policy_markdown: str) -> str:
    return "\n".join(
        [
            report_body.rstrip(),
            "",
            "---",
            "",
            "## Policy-grounded recommendations",
            "",
            "> AI-assisted analysis using operational and failure metrics plus retrieved policy excerpts "
            "from the vector store.",
            "",
            policy_markdown.rstrip(),
            "",
            "---",
            "",
            "_Generated automatically by the support analysis system._",
        ]
    )


def _unique_report_path(report_dir: str) -> str:
    """Use report_YYYY_MM_DD.md; if taken, report_YYYY_MM_DD_<timestamp>.md."""
    date_str = datetime.now().strftime("%Y_%m_%d")
    base = f"report_{date_str}"
    ext = ".md"
    candidate = os.path.join(report_dir, f"{base}{ext}")
    if not os.path.exists(candidate):
        return candidate
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return os.path.join(report_dir, f"{base}_{ts}{ext}")


def node_5_generate_report(state: dict) -> dict:
    print("Generating report.......")
    try:
        ops, fail = _ops_and_failure(state)
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_body = pool.submit(generate_report_body, state)
            fut_policy = pool.submit(generate_policy_reasoning_markdown, ops, fail)
            report_body = fut_body.result()
            policy_md = fut_policy.result()
        markdown_body = _assemble_full_report(report_body, policy_md)

        report_dir = "assets/reports"
        os.makedirs(report_dir, exist_ok=True)
        file_path = _unique_report_path(report_dir)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_body)

        print(f"Report written to: {file_path}")

        return {
            **state,
            "report": markdown_body,
            "report_file": file_path,
        }

    except Exception as e:
        print(f"Error generating report: {e}")
        return {
            **state,
            "error": str(e),
        }
