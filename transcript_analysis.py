from concurrent.futures import ThreadPoolExecutor
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from db import store_transcript_analyses
from state.transcript_analysis_schema import TranscriptAnalysis

load_dotenv()

TRANSCRIPT_ANALYSIS_SYSTEM_MESSAGE = """
    You are an internal support operations analyst for a movie theater chain.
    Analyze the transcript and fill the structured fields. Use only the allowed enum values and numbers; keep text short except summary_of_issue.

    Time (in seconds, estimate from message flow if not explicit):
    - time_spent_with_chatbot_seconds: time user spent interacting with the chatbot only.
    - time_spent_with_human_seconds: time user spent with a human agent only.
    - time_spent_waiting_seconds: time waiting for reply or in queue.

    Resolution:
    - resolution_stage: how the chat ended (use ResolutionStage enum).
    - If a refund was issued, set resolution_stage to resolved.

    User tone (from wording and cues):
    - user_sentiment: use UserSentiment enum.

    Where resolution broke down (use not_applicable if that party resolved it):
    - stage_chatbot_failed: at what point the chatbot could not resolve (use PointFailed enum).
    - stage_human_failed: at what point the human could not resolve (use PointFailed enum; not_applicable if no human or human resolved).

    Root cause and fix:
    - reason_failed_to_resolve: if unresolved, pick the specific reason from the allowed enum ReasonFailed
    - what_could_fix: what would have fixed this enum WhatCouldFix not_applicable if resolved.

    Other:
    - issuesIdentified: short list of issue labels (use IssueIdentified enum).
    - summary_of_issue: 2–4 sentences on what happened and the outcome (only field that can be longer).
    - issueIdentifiedByChatbot / issueIdentifiedByHumanAgent: true only if that agent clearly identified and stated the issue.
    Be strict: only use enum values listed; estimate times from turn-taking when not stated.
    """

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# This runnable forces the LLM to return JSON matching TranscriptAnalysis and parses it
structured_model = model.with_structured_output(TranscriptAnalysis)


def analyze_transcript(transcript: str) -> TranscriptAnalysis:
    system_message = TRANSCRIPT_ANALYSIS_SYSTEM_MESSAGE
    path_to_transcript = f"assets/transcripts/{transcript}.txt"
    with open(path_to_transcript, "r") as file:
        transcript_content = file.read()
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=f"Transcript id: {transcript}\n\n{transcript_content}"),
    ]
    # Invoke the structured runnable so the response is a TranscriptAnalysis instance
    return structured_model.invoke(messages)


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
