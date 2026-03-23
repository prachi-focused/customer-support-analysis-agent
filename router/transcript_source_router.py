"""Route at graph entry: run LLM on transcript files vs load prior analyses from Postgres."""

from db import transcript_analyses_is_empty


def transcript_source_router(state: dict) -> str:
    """
    If ``transcript_analyses`` is empty, go straight to fresh analysis (nothing to reuse).

    Otherwise ask whether to run a new transcript analysis or reuse rows from the DB.

    Returns the next node name.
    """
    try:
        if transcript_analyses_is_empty():
            print(
                "No transcript analyses in the database; running node_1_transcript_analysis."
            )
            return "node_1_transcript_analysis"
    except Exception as e:
        print(
            f"Could not check transcript_analyses ({e}); falling back to interactive choice."
        )

    print("Run a new transcript analysis (yes), or reuse stored analyses from the database (no)?")
    raw = input("New analysis? (yes/no): ").strip().lower()
    while raw not in ("yes", "y", "no", "n"):
        print("Invalid answer. Please enter yes or no (or y/n).")
        raw = input("New analysis? (yes/no): ").strip().lower()

    if raw in ("yes", "y"):
        return "node_1_transcript_analysis"
    return "node_0_load_transcripts_from_db"
