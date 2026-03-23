from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from state import CustomerSupportProcess
from node_0_load_transcripts_from_db import node_0_load_transcripts_from_db
from node_1_transcript_analysis import node_1_transcript_analysis
from node_2_policy_update import node_2_policy_update
from node_3_calculate_operations_metrics import node_3_calculate_operations_metrics
from node_4_calculate_failure_metrics import node_4_calculate_failure_metrics
from node_5_generate_report import node_5_generate_report
from router import policy_update_router, transcript_source_router

load_dotenv()
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

message = [HumanMessage(content="Analyze the transcript and return the analysis.", role="user")]


builder = StateGraph(CustomerSupportProcess)
builder.add_node("node_0_load_transcripts_from_db", node_0_load_transcripts_from_db)
builder.add_node("node_1_transcript_analysis", node_1_transcript_analysis)
builder.add_node("node_2_policy_update", node_2_policy_update)
builder.add_node("node_3_calculate_operations_metrics", node_3_calculate_operations_metrics)
builder.add_node("node_4_calculate_failure_metrics", node_4_calculate_failure_metrics)
builder.add_node("node_5_generate_report", node_5_generate_report)

builder.add_conditional_edges(START, transcript_source_router)
builder.add_conditional_edges("node_1_transcript_analysis", policy_update_router)
builder.add_conditional_edges("node_0_load_transcripts_from_db", policy_update_router)

builder.add_edge("node_2_policy_update", "node_3_calculate_operations_metrics")
builder.add_edge("node_3_calculate_operations_metrics", "node_4_calculate_failure_metrics")
builder.add_edge("node_4_calculate_failure_metrics", "node_5_generate_report")
builder.add_edge("node_5_generate_report", END)

graph = builder.compile()

# Invoke with messages and optional transcripts list
transcripts = [
    "transcript_01",
    "transcript_02",
    "transcript_03",
    "transcript_04",
    "transcript_05",
    "transcript_06",
    "transcript_07",
    "transcript_08",
    "transcript_09",
    "transcript_10",
    "transcript_11",
    "transcript_12",
    "transcript_13",
    "transcript_14",
]
response = graph.invoke({"messages": message, "transcripts": transcripts, "path_to_transcripts": "assets/transcripts/"})
# for analysis in response["transcript_analysis"]:
#     print("-" * 100)
#     print("Transcript Analysis:")
#     print(f"Transcript ID: {analysis.transcriptId}")
#     print(f"Issues Identified: {analysis.issuesIdentified}")
#     print(f"Issue identification time: {analysis.issueIdentificationTime}s")
#     print(f"Summary: {analysis.summary_of_issue}")
#     print(f"Issue identified by chatbot: {analysis.issueIdentifiedByChatbot} | by human: {analysis.issueIdentifiedByHumanAgent}")
#     print(f"Time with chatbot: {analysis.time_spent_with_chatbot_seconds}s | with human: {analysis.time_spent_with_human_seconds}s | waiting: {analysis.time_spent_waiting_seconds}s")
#     print(f"Resolution: {analysis.resolution_stage} | User sentiment: {analysis.user_sentiment}")
#     print(f"Stage chatbot failed: {analysis.stage_chatbot_failed} | Stage human failed: {analysis.stage_human_failed}")
#     print(f"Failure reasons: {analysis.failure_reasons} | What could fix: {analysis.what_could_fix}")
#     print("-" * 100)
