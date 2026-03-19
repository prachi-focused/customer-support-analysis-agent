"""
Failure-focused metrics from transcript analyses (reason_failed_to_resolve + user_sentiment).
"""


def node_4_calculate_failure_metrics(state: dict) -> dict:
    print("Calculating failure metrics.......")
    analyses = state.get("transcript_analysis") or []
    try:
        failure_metrics = compute_failure_metrics(analyses)
        print("----------->>>>>><<<<<<<-------------")
        print(failure_metrics)
    except Exception as e:
        failure_metrics = {
            "error": str(e),
        }
    return {"failure_metrics": failure_metrics}
