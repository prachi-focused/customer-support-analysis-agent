from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from uuid import uuid4

from node_0_load_transcripts_from_db import node_0_load_transcripts_from_db
from node_1_transcript_analysis import node_1_transcript_analysis
from node_2_policy_update import node_2_policy_update
from node_3_calculate_operations_metrics import node_3_calculate_operations_metrics
from node_4_calculate_failure_metrics import node_4_calculate_failure_metrics
from node_5_generate_report import node_5_generate_report
from router import policy_update_router, transcript_source_router
from state import CustomerSupportProcess

load_dotenv()


def node_0_route_transcript_source(state: dict) -> dict:
    decision = transcript_source_router(state)
    if decision == "node_1_transcript_analysis":
        return {"transcript_source_choice": "run_new_analysis"}
    return {"transcript_source_choice": "load_from_db"}


def node_3_route_policy_update(state: dict) -> dict:
    decision = policy_update_router(state)
    if decision == "node_2_policy_update":
        return {"policy_update_choice": "run_policy_update"}
    return {"policy_update_choice": "skip_policy_update"}


def route_from_node_0(state: dict) -> str:
    return str(state.get("transcript_source_choice", "run_new_analysis"))


def route_from_node_3(state: dict) -> str:
    return str(state.get("policy_update_choice", "run_policy_update"))


def node_5_metrics_fanout(_: dict) -> dict:
    """Explicit fanout node so Studio can visualize parallel metrics branches."""
    return {}


def build_graph():
    builder = StateGraph(CustomerSupportProcess)
    builder.add_node("node_0_route_transcript_source", node_0_route_transcript_source)
    builder.add_node("node_1_load_transcripts_from_db", node_0_load_transcripts_from_db)
    builder.add_node("node_2_transcript_analysis", node_1_transcript_analysis)
    builder.add_node("node_3_route_policy_update", node_3_route_policy_update)
    builder.add_node("node_4_policy_update", node_2_policy_update)
    builder.add_node("node_5_metrics_fanout", node_5_metrics_fanout)
    builder.add_node("node_6_calculate_operations_metrics", node_3_calculate_operations_metrics)
    builder.add_node("node_7_calculate_failure_metrics", node_4_calculate_failure_metrics)
    builder.add_node("node_8_generate_report", node_5_generate_report)

    builder.add_edge(START, "node_0_route_transcript_source")
    builder.add_conditional_edges(
        "node_0_route_transcript_source",
        route_from_node_0,
        {
            "run_new_analysis": "node_2_transcript_analysis",
            "load_from_db": "node_1_load_transcripts_from_db",
        },
    )

    builder.add_edge("node_2_transcript_analysis", "node_3_route_policy_update")
    builder.add_edge("node_1_load_transcripts_from_db", "node_3_route_policy_update")
    builder.add_conditional_edges(
        "node_3_route_policy_update",
        route_from_node_3,
        {
            "run_policy_update": "node_4_policy_update",
            "skip_policy_update": "node_5_metrics_fanout",
        },
    )

    builder.add_edge("node_4_policy_update", "node_5_metrics_fanout")
    builder.add_edge("node_5_metrics_fanout", "node_6_calculate_operations_metrics")
    builder.add_edge("node_5_metrics_fanout", "node_7_calculate_failure_metrics")
    builder.add_edge("node_6_calculate_operations_metrics", "node_8_generate_report")
    builder.add_edge("node_7_calculate_failure_metrics", "node_8_generate_report")
    builder.add_edge("node_8_generate_report", END)
    return builder.compile()


graph = build_graph()


if __name__ == "__main__":
    # Invoke with messages and optional transcripts list
    message = [HumanMessage(content="Analyze the transcript and return the analysis.", role="user")]
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
    response = graph.invoke(
        {"messages": message, "transcripts": transcripts, "path_to_transcripts": "assets/transcripts/"},
        config={"configurable": {"thread_id": f"run-{uuid4()}"}},
    )
