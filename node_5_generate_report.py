"""Report generation node for the LangGraph workflow."""

import os
from datetime import datetime


def generate_report(state: dict) -> str:
    """Return the full Markdown document body. Format here or build from `state`."""
    return "# Report\n\nReport generated successfully.\n"


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
        markdown_body = generate_report(state)

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
