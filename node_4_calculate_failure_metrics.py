"""
Failure-focused metrics from transcript analyses (failure_reasons + user_sentiment).
"""

from collections import Counter
from typing import Any

from state.transcript_analysis_schema import FailureReasonItem, TranscriptAnalysis


def _failure_items(analysis: Any) -> list[FailureReasonItem]:
    if isinstance(analysis, TranscriptAnalysis):
        return list(analysis.failure_reasons)
    raw = analysis.get("failure_reasons") if isinstance(analysis, dict) else []
    if not raw:
        return []
    out: list[FailureReasonItem] = []
    for item in raw:
        if isinstance(item, FailureReasonItem):
            out.append(item)
        elif isinstance(item, dict):
            out.append(FailureReasonItem.model_validate(item))
    return out


def compute_failure_metrics(analyses: list[Any]) -> dict[str, Any]:
    by_category: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    with_any = 0

    for a in analyses:
        items = _failure_items(a)
        if items:
            with_any += 1
        for it in items:
            by_reason[it.reason.value] += 1
            by_category[it.category] += 1

    total = len(analyses)
    return {
        "total_transcripts": total,
        "transcripts_with_failure_reasons": with_any,
        "failure_reason_mentions_by_category": dict(by_category),
        "failure_reason_mentions_by_reason": dict(by_reason),
    }


def node_4_calculate_failure_metrics(state: dict) -> dict:
    print("Calculating failure metrics.......")
    analyses = state.get("transcript_analysis") or []
    try:
        failure_metrics = compute_failure_metrics(analyses)
        print("----------->>>>>><<<<<<<-------------")
        print(failure_metrics)
    except Exception as e:
        failure_metrics = {
            "error": str(e),
        }
    return {"failure_metrics": failure_metrics}
