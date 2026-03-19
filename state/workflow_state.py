from __future__ import annotations

from langgraph.graph.message import MessagesState

from .transcript_analysis_schema import TranscriptAnalysis


class CustomerSupportProcess(MessagesState):
    """LangGraph state for the customer support workflow."""

    transcript_analysis: list[TranscriptAnalysis] = []
    transcripts: list[str] = []
    operations_metrics: dict = {}
