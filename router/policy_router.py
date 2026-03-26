"""Route after transcript analysis: optional policy store update vs metrics."""

from db import policy_txt_chunks_is_empty


def policy_update_router(state: dict) -> str | list[str]:
    """
    If the policy vector store has no TXT-ingested chunks, run policy ingest first.

    Otherwise ask whether to update the policy store or skip to metrics.

    Returns next node(s): either policy update, or both metrics nodes in parallel.
    """
    try:
        if policy_txt_chunks_is_empty():
            print(
                "No policy_txt chunks in the vector store; running node_2_policy_update."
            )
            return "node_2_policy_update"
    except Exception as e:
        print(
            f"Could not check policy_chunks ({e}); falling back to interactive choice."
        )

    raw = input("Update policy store? (yes/no): ").strip().lower()
    while raw not in ("yes", "y", "no", "n"):
        print("Invalid answer. Please enter yes or no.")
        raw = input("Update policy store? (yes/no): ").strip().lower()

    if raw in ("yes", "y"):
        return "node_2_policy_update"

    return [
        "node_3_calculate_operations_metrics",
        "node_4_calculate_failure_metrics",
    ]
