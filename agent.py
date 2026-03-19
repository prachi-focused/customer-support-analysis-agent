from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from transcript_analysis import transcript_analysis_node, CustomerSupportProcess
from policy_update import node_2_policy_update
from calculate_metrics import node_3_calculate_metrics
from generate_report import node_4_generate_report

load_dotenv()
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

message = [HumanMessage(content="Analyze the transcript and return the analysis.", role="user")]


def policy_update_router(state: dict) -> str:
    """
    After transcript analysis: route by human input only.
    Decides whether to update the policy store or skip it and go to calculate metrics.
    Returns the next node name.
    """
    
    raw = input("Update policy store? (yes/no): ").strip().lower()
    while raw not in ("yes", "y", "no", "n"):
        print("Invalid answer. Please enter yes or no.")
        raw = input("Update policy store? (yes/no): ").strip().lower()
    
    if raw in ("yes", "y"):
        return "node_2_policy_update"
    
    return "node_3_calculate_metrics"


builder = StateGraph(CustomerSupportProcess)
builder.add_node("node_1_transcript_analysis", transcript_analysis_node)
builder.add_node("node_2_policy_update", node_2_policy_update)
builder.add_node("node_3_calculate_metrics", node_3_calculate_metrics)
builder.add_node("node_4_generate_report", node_4_generate_report)

builder.add_edge(START, "node_1_transcript_analysis")

builder.add_conditional_edges(
    "node_1_transcript_analysis",
    policy_update_router,
)

builder.add_edge("node_2_policy_update", "node_3_calculate_metrics")
builder.add_edge("node_3_calculate_metrics", "node_4_generate_report")
builder.add_edge("node_4_generate_report", END)

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
    "transcript_10"
]
response = graph.invoke({"messages": message, "transcripts": transcripts})
for analysis in response["transcript_analysis"]:
    print("-" * 100)
    print("Transcript Analysis:")
    print(f"Transcript ID: {analysis.transcriptId}")
    print(f"Issues Identified: {analysis.issuesIdentified}")
    print(f"Issue identification time: {analysis.issueIdentificationTime}s")
    print(f"Summary: {analysis.summary_of_issue}")
    print(f"Issue identified by chatbot: {analysis.issueIdentifiedByChatbot} | by human: {analysis.issueIdentifiedByHumanAgent}")
    print(f"Time with chatbot: {analysis.time_spent_with_chatbot_seconds}s | with human: {analysis.time_spent_with_human_seconds}s | waiting: {analysis.time_spent_waiting_seconds}s")
    print(f"Resolution: {analysis.resolution_stage} | User sentiment: {analysis.user_sentiment}")
    print(f"Stage chatbot failed: {analysis.stage_chatbot_failed} | Stage human failed: {analysis.stage_human_failed}")
    print(f"Reason failed: {analysis.reason_failed_to_resolve} | What could fix: {analysis.what_could_fix}")
    print("-" * 100)