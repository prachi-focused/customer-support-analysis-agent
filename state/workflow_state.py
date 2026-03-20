from __future__ import annotations

from langgraph.graph.message import MessagesState

from .transcript_analysis_schema import TranscriptAnalysis


class CustomerSupportProcess(MessagesState):
    """LangGraph state for the customer support workflow."""

    transcript_analysis: list[TranscriptAnalysis] = []
    transcripts: list[str] = []
    path_to_transcripts: str = "assets/transcripts/"
    operations_metrics: dict = {}
    failure_metrics: dict = {}
