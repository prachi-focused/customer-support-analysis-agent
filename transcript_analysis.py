from typing import Literal
from concurrent.futures import ThreadPoolExecutor
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph.message import MessagesState
from dotenv import load_dotenv
from pydantic import BaseModel

from db import store_transcript_analyses

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
# Short enums for structured answers (no long text except summary)
ResolutionStage = Literal[
    "chatbot_resolved",
    "human_resolved",
    "unresolved",
    "escalated_no_resolution",
    "user_abandoned",
    "transferred_only",
    "partial_resolution"
]
UserSentiment = Literal["happy", "satisfied", "neutral", "frustrated", "irritated", "sad", "angry", "unknown"]
PointFailed = Literal[
    "not_applicable",
    "could_not_identify",
    "policy_denied",
    "wrong_info",
    "could_not_process",
    "suggested_handoff_to_human",
    "timeout_waiting_for_user_response",
    "timeout_waiting_for_support_agent_response",
    "timeout_waiting_for_chatbot_response",
    "user_left_conversation",
    "other",
]
ReasonFailed = Literal[
    "not_applicable",
    # Policy / business rules
    "policy_violation",
    "policy_does_not_allow_request",
    "refund_window_expired",
    "eligibility_criteria_not_met",
    # System / technical
    "system_error",
    "payment_system_failure",
    "booking_system_error",
    "chatbot_or_integration_down",
    "session_or_timeout_error",
    # User left or disengaged
    "user_left_conversation",
    "user_abandoned_mid_flow",
    "user_closed_chat_without_resolution",
    # User-provided info issues
    "user_misunderstanding_policy",
    "user_provided_invalid_information",
    "user_provided_incomplete_information",
    "user_provided_wrong_account_or_order_details",
    "user_request_outside_scope",
    # Agent process / knowledge / capability
    "agent_did_not_follow_process",
    "agent_skipped_verification_step",
    "agent_inadequate_knowledge",
    "agent_lacked_authority_to_resolve",
    "agent_inadequate_capabilities",
    "agent_tool_or_system_access_limited",
    # Chatbot knowledge / capability
    "chatbot_inadequate_knowledge",
    "chatbot_inadequate_capabilities",
    "agent_could_not_access_user_data",
    "agent_missing_tool_or_integration",
    "chatbot_could_not_access_user_data",
    "chatbot_missing_tool_or_integration",
    # Agent/human communication failures (replacing vague "agent_miscommunication")
    "agent_gave_incorrect_or_confusing_instructions",
    "agent_misunderstood_user_request",
    "agent_used_jargon_or_unclear_language",
    "agent_failed_to_confirm_understanding",
    # Chatbot communication failures (replacing "chatbot_miscommunication")
    "chatbot_interpreted_request_incorrectly",
    "chatbot_gave_ambiguous_or_wrong_response",
    "chatbot_repeated_unhelpful_answer",
    "chatbot_did_not_acknowledge_user_concern",
    # User-side communication issues (replacing "user_miscommunication")
    "user_request_was_ambiguous",
    "user_changed_or_clarified_request_mid_flow",
    "user_did_not_provide_required_details",
    "user_expectations_mismatch",
    "other",
]
WhatCouldFix = Literal[
    "not_applicable",
    "policy_change",
    "chatbot_training",
    "faster_handoff",
    "clearer_messaging",
    "tool_access",
    "other",
]


class TranscriptAnalysis(BaseModel):
    transcriptId: str
    issuesIdentified: list[str]  # short labels, e.g. ["refund", "email not received"]

    issueIdentificationTime: float  # seconds to identify issue
    summary_of_issue: str  # only lengthy field: what happened and outcome

    issueIdentifiedByChatbot: bool
    issueIdentifiedByHumanAgent: bool

    time_spent_with_chatbot_seconds: float
    time_spent_with_human_seconds: float
    time_spent_waiting_seconds: float

    resolution_stage: ResolutionStage

    user_sentiment: UserSentiment  # from tone of user messages

    stage_chatbot_failed: PointFailed  # at what point chatbot could not resolve (or not_applicable)
    stage_human_failed: PointFailed  # at what point human could not resolve (or not_applicable)

    reason_failed_to_resolve: ReasonFailed  # specific reason if unresolved
    what_could_fix: WhatCouldFix  # what could have fixed this

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


class CustomerSupportProcess(MessagesState):
    """LangGraph state for the customer support workflow."""
    transcript_analysis: list["TranscriptAnalysis"] = []
    transcripts: list[str] = []
    operations_metrics: dict = {}


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