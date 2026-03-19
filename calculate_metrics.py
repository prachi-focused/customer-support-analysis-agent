"""Outcome metrics from `state["transcript_analysis"]` for the current graph run."""

from __future__ import annotations

from collections import Counter
from typing import Any, get_args

from state.transcript_analysis_schema import (
    RESOLVED_RESOLUTION_STAGES,
    ResolutionStage,
    TranscriptAnalysis,
)

_ORDERED_STAGES: tuple[str, ...] = tuple(get_args(ResolutionStage))

# Calculate percentage
def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 1)

# Get resolution stage of a transcript analysis
def _resolution_stage_of(item: Any) -> str:
    if isinstance(item, TranscriptAnalysis):
        return item.resolution_stage or "unknown"
    if isinstance(item, dict):
        return str(item.get("resolution_stage") or "unknown")
    return str(getattr(item, "resolution_stage", None) or "unknown")

# Count by resolution stage enum : ResolutionStage
def count_by_resolution_stage(analyses: list[Any]) -> dict[str, int]:
    known = set(_ORDERED_STAGES)
    counter: Counter[str] = Counter()
    for a in analyses:
        stage = _resolution_stage_of(a)
        if stage not in known:
            stage = "unknown"
        counter[stage] += 1
    return dict(counter)

# Build outcome KPIs
def build_outcome_kpis(stage_counts: dict[str, int], total: int) -> dict[str, Any]:
    resolved_total = sum(
        stage_counts.get(s, 0) for s in RESOLVED_RESOLUTION_STAGES
    )

    return {
        "total_transcripts": total,
        "resolved_total": resolved_total,
        "overall_resolution_rate_pct": _percentage(resolved_total, total),
        "chatbot_resolved_count": stage_counts.get("chatbot_resolved", 0),
        "human_resolved_count": stage_counts.get("human_resolved", 0),
        "unresolved_count": stage_counts.get("unresolved", 0),
        "user_abandoned_count": stage_counts.get("user_abandoned", 0),
        "escalated_no_resolution_count": stage_counts.get("escalated_no_resolution", 0),
        "transferred_only_count": stage_counts.get("transferred_only", 0),
        "partial_resolution_count": stage_counts.get("partial_resolution", 0),
        "unknown_stage_count": stage_counts.get("unknown", 0),
        "chatbot_resolved_rate_pct": _percentage(
            stage_counts.get("chatbot_resolved", 0), total
        ),
        "human_resolved_rate_pct": _percentage(
            stage_counts.get("human_resolved", 0), total
        ),
    }

# Build resolution stage breakdown
def build_resolution_stage_breakdown(
    stage_counts: dict[str, int], total: int
) -> list[dict[str, Any]]:
    ordered = list(_ORDERED_STAGES) + ["unknown"]
    return [
        {
            "resolution_stage": stage,
            "count": (n := stage_counts.get(stage, 0)),
            "pct_of_total": _percentage(n, total),
        }
        for stage in ordered
    ]


def compute_operations_metrics(analyses: list[Any]) -> dict[str, Any]:
    total = len(analyses)
    stage_counts = count_by_resolution_stage(analyses)
    return {
        "outcome_kpis": build_outcome_kpis(stage_counts, total),
        "resolution_stage_breakdown": build_resolution_stage_breakdown(stage_counts, total),
    }

def compute_issues_metrics(analyses: list[Any]) -> dict[str, Any]:
    return {
        "issues_metrics": "",
    }


def node_3_calculate_metrics(state: dict) -> dict:
    print("Calculating metrics.......")
    analyses = state.get("transcript_analysis") or []

    try:
        
        operations_metrics = compute_operations_metrics(analyses)
        print("----------->>>>>><<<<<<<-------------")
        print(operations_metrics)

        issues_metrics = compute_issues_metrics(analyses)
        print("----------->>>>>><<<<<<<-------------")
        print(issues_metrics)

        payload = {
            "operations_metrics": operations_metrics,
            "issues_metrics": issues_metrics,
        }
    except Exception as e:
        payload = {
            "operations_metrics": {},
            "error": str(e),
        }


    return payload
