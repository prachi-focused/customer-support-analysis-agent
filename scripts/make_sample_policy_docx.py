#!/usr/bin/env python3
"""Write a minimal sample policy .txt into assets/policies/ for testing ingest."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "policies" / "sample_policy.txt"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        f.write("Returns\nCustomers may return unused items within 30 days of purchase with receipt.\nShipping\nStandard shipping is 5–7 business days. Express available at checkout.")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
