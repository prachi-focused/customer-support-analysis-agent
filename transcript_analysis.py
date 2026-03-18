from typing import Literal
from concurrent.futures import ThreadPoolExecutor
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph.message import MessagesState
from dotenv import load_dotenv
from pydantic import BaseModel

from db import store_transcript_analyses

load_dotenv()

class TranscriptAnalysis(BaseModel):
    transcriptId: str
    issuesIdentified: list[str] # list of issues identified in the transcript

    issueIdentificationTime: float # time taken to identify the issue in seconds
    summary_of_issue: str

    issueIdentifiedByChatbot: bool
    issueIdentifiedByHumanAgent: bool

    resolution_stage: Literal["chatbot_resolved", "human_agent_resolved", "unresolved"]
    
    time_spent_on_issue: float # time spent on the issue in seconds
    bottleneck_category: Literal[
        "policy_restriction",
        "chatbot_knowledge_gap",
        "chatbot_missing_tool_access",
        "manual_approval_required",
        "user_input_error",
        "communication_error",
        "unknown",
    ]
    user_feedback: Literal[
        "positive",
        "negative",
        "neutral",
        "unknown",
    ]

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# This runnable forces the LLM to return JSON matching TranscriptAnalysis and parses it
structured_model = model.with_structured_output(TranscriptAnalysis)


def analyze_transcript(transcript: str) -> TranscriptAnalysis:
    system_message = """
    You are an internal support operations analyst for a movie theater chain.
    Analyze the provided support transcript and produce structured output.

    Rules:
    - Pick exactly one issue category
    - Mark resolved=true only when the transcript clearly ends in a resolution
    - resolution_stage must be chatbot, human_agent, or unresolved
    - escalated_to_human=true if a human agent joined
    - time_spent_on_issue is the total time spent on the issue in seconds
    - issueIdentifiedByChatbot only if the issue is identified by the chatbot and it confirms the issue.
    - issueIdentifiedByHumanAgent only if the issue is identified by the human agent and they confirm the issue.
    - refund_related=true if the issue involves a refund or charge reversal
    - Pick the most likely operational bottleneck
    - Be concise and grounded only in the transcript
    - In the summary_of_issue, mention the issue and what steps were taken to resolve it.
    """
    path_to_transcript = f"assets/transcripts/{transcript}.txt"
    with open(path_to_transcript, "r") as file:
        transcript_content = file.read()
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=f"Transcript id: {transcript}\n\n{transcript_content}"),
    ]
    # Invoke the structured runnable so the response is a TranscriptAnalysis instance
    return structured_model.invoke(messages)


class CustomerSupportProcess(MessagesState):
    """LangGraph state for the customer support workflow."""
    transcript_analysis: list["TranscriptAnalysis"] = []
    transcripts: list[str] = []


MAX_CONCURRENCY = 5


def transcript_analysis_node(state: dict) -> dict:
    """
    LangGraph node: runs transcript analysis (up to MAX_CONCURRENCY in parallel),
    stores results in the local Postgres DB when available, and returns a state update.
    """
    print("Running transcript analysis node...")
    transcript_ids = state.get("transcripts", ["transcript_01"])
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
        analysis = list(executor.map(analyze_transcript, transcript_ids))
    try:
        store_transcript_analyses([a.model_dump() for a in analysis])
    except Exception as e:
        # DB optional: run without Postgres (e.g. connection refused, no password)
        import warnings
        warnings.warn(f"Could not store analyses in DB (skipping): {e}", stacklevel=0)
    return {"transcript_analysis": analysis}


# if __name__ == "__main__":
#     state = {"transcripts": ["transcript_01"]}
#     update = transcript_analysis_node(state)
#     transcript_analysis = update["transcript_analysis"]
#     for analysis in transcript_analysis:
#         print("-" * 100)
#         print("Transcript Analysis:")
#         print(f"Transcript ID: {analysis.transcriptId}")
#         print(f"Issues Identified: {analysis.issuesIdentified}")
#         print(f"Time Spent on Issue: {analysis.time_spent_on_issue} seconds")
#         print(f"Summary of Issue: {analysis.summary_of_issue}")
#         print(f"Issue Identified By Chatbot: {analysis.issueIdentifiedByChatbot}")
#         print(f"Issue Identified By Human Agent: {analysis.issueIdentifiedByHumanAgent}")
#         print(f"Resolution Stage: {analysis.resolution_stage}")
#         print(f"Bottleneck Category: {analysis.bottleneck_category}")
#         print(f"User Feedback: {analysis.user_feedback}")
#         print("-" * 100)