from typing import Literal

from pydantic import BaseModel

# Short enums for structured answers (no long text except summary)
ResolutionStage = Literal[
    "chatbot_resolved",
    "human_resolved",
    "unresolved",
    "escalated_no_resolution",
    "user_abandoned",
    "transferred_only",
    "partial_resolution",
    "refund_processed",
    "unknown",
]
UserSentiment = Literal[
    "happy",
    "satisfied",
    "neutral",
    "frustrated",
    "irritated",
    "sad",
    "angry",
    "unknown",
]
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
FailureCategory = Literal[
    "not_applicable",
    "policy",
    "system_tooling",
    "knowledge_capability",
    "communication",
    "user_behavior",
    "chat_abandoned",
    "other"
]
REASON_TO_CATEGORY = {
    # Policy
    "policy_violation": "policy",
    "policy_does_not_allow_request": "policy",
    "refund_window_expired": "policy",
    "eligibility_criteria_not_met": "policy",

    # System / tooling
    "system_error": "system_tooling",
    "payment_system_failure": "system_tooling",
    "booking_system_error": "system_tooling",
    "chatbot_or_integration_down": "system_tooling",
    "session_or_timeout_error": "system_tooling",
    "agent_missing_tool_or_integration": "system_tooling",
    "chatbot_missing_tool_or_integration": "system_tooling",
    "agent_tool_or_system_access_limited": "system_tooling",
    "agent_could_not_access_user_data": "system_tooling",
    "chatbot_could_not_access_user_data": "system_tooling",

    # Knowledge / capability
    "agent_inadequate_knowledge": "knowledge_capability",
    "chatbot_inadequate_knowledge": "knowledge_capability",
    "agent_inadequate_capabilities": "knowledge_capability",
    "chatbot_inadequate_capabilities": "knowledge_capability",
    "agent_lacked_authority_to_resolve": "knowledge_capability",

    # Communication
    "agent_gave_incorrect_or_confusing_instructions": "communication",
    "agent_misunderstood_user_request": "communication",
    "agent_used_jargon_or_unclear_language": "communication",
    "agent_failed_to_confirm_understanding": "communication",
    "chatbot_interpreted_request_incorrectly": "communication",
    "chatbot_gave_ambiguous_or_wrong_response": "communication",
    "chatbot_repeated_unhelpful_answer": "communication",
    "chatbot_did_not_acknowledge_user_concern": "communication",

    # User behavior / input
    "user_misunderstanding_policy": "user_behavior",
    "user_provided_invalid_information": "user_behavior",
    "user_provided_incomplete_information": "user_behavior",
    "user_provided_wrong_account_or_order_details": "user_behavior",
    "user_request_outside_scope": "user_behavior",
    "user_request_was_ambiguous": "user_behavior",
    "user_changed_or_clarified_request_mid_flow": "user_behavior",
    "user_did_not_provide_required_details": "user_behavior",
    "user_expectations_mismatch": "user_behavior",

    # Abandonment
    "user_left_conversation": "abandonment",
    "user_abandoned_mid_flow": "abandonment",
    "user_closed_chat_without_resolution": "abandonment",

    # Process issues (optional bucket)
    "agent_did_not_follow_process": "knowledge_capability",
    "agent_skipped_verification_step": "knowledge_capability",

    # Default
    "other": "other",
    "not_applicable": "other",
}
WhatCouldFix = Literal[
    "not_applicable",
    "policy_change",
    "chatbot_training",
    "faster_handoff",
    "clearer_messaging",
    "tool_access",
    "other",
]

# Stages counted as resolved for aggregate metrics (subset of ResolutionStage values).
RESOLVED_RESOLUTION_STAGES: frozenset[str] = frozenset(
    {"chatbot_resolved", "human_resolved", "refund_processed"}
)


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

    reason_failed_to_resolve: str  # specific reason if unresolved
    what_could_fix: str  # what could have fixed this
