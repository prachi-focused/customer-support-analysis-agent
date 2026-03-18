from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from transcript_analysis import transcript_analysis_node, CustomerSupportProcess
from policy_update import node_2_policy_update

load_dotenv()
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

message = [HumanMessage(content="Analyze the transcript and return the analysis.", role="user")]


def human_policy_router(state: dict) -> str:
    """
    After transcript analysis: route by human input only (nothing written to state).
    Returns the next node name or END.
    """
    raw = input("Update policy store? (yes/no): ").strip().lower()
    while raw not in ("yes", "y", "no", "n"):
        print("Invalid answer. Please enter yes or no.")
        raw = input("Update policy store? (yes/no): ").strip().lower()
    if raw in ("yes", "y"):
        return "node_2_policy_update"
    return "done"


builder = StateGraph(CustomerSupportProcess)
builder.add_node("node_1_transcript_analysis", transcript_analysis_node)
builder.add_node("node_2_policy_update", node_2_policy_update)

builder.add_edge(START, "node_1_transcript_analysis")

builder.add_conditional_edges(
    "node_1_transcript_analysis",
    human_policy_router,
    {
        "node_2_policy_update": "node_2_policy_update", 
        "done": END
    },
)
builder.add_edge("node_2_policy_update", END)
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
# for analysis in response["transcript_analysis"]:
#     print("-" * 100)
#     print("Transcript Analysis:")
#     print(f"Transcript ID: {analysis.transcriptId}")
#     print(f"Issues Identified: {analysis.issuesIdentified}")
#     print(f"Time Spent on Issue: {analysis.time_spent_on_issue} seconds")
#     print(f"Summary of Issue: {analysis.summary_of_issue}")
#     print(f"Issue Identified By Chatbot: {analysis.issueIdentifiedByChatbot}")
#     print(f"Issue Identified By Human Agent: {analysis.issueIdentifiedByHumanAgent}")
#     print(f"Resolution Stage: {analysis.resolution_stage}")
#     print(f"Bottleneck Category: {analysis.bottleneck_category}")
#     print(f"User Feedback: {analysis.user_feedback}")
#     print("-" * 100)