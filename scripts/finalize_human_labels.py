"""Convert the filled-in labeling_worksheet.csv into results/block8/human_labels.jsonl.

Validates before writing anything:
  - every row has a non-empty human_score
  - human_score is exactly one of: pass, partial, fail
  - every row has non-empty human_reasoning
  - all 50 scenario_ids from the coverage run are present

If validation fails, nothing is written and the specific problem rows are
printed so you can go fix them in the CSV and re-run.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSHEET = ROOT / "results" / "block8" / "labeling_worksheet.csv"
COVERAGE_RUN = ROOT / "results" / "block8" / "coverage_2026-09-02.json"
OUTPUT = ROOT / "results" / "block8" / "human_labels.jsonl"

VALID_SCORES = {"pass", "partial", "fail"}


def main():
    if not WORKSHEET.exists():
        print(f"ERROR: {WORKSHEET} not found. Run build_labeling_worksheet.py first.")
        return

    with open(COVERAGE_RUN) as f:
        expected_ids = {r["scenario_id"] for r in json.load(f)["individual_results"]}

    with open(WORKSHEET, newline="") as f:
        rows = list(csv.DictReader(f))

    errors = []
    seen_ids = set()

    for i, row in enumerate(rows, 1):
        sid = row.get("scenario_id", "").strip()
        score = row.get("human_score", "").strip()
        reasoning = row.get("human_reasoning", "").strip()

        if not sid:
            errors.append(f"Row {i}: missing scenario_id")
            continue
        seen_ids.add(sid)

        if not score:
            errors.append(f"Row {i} ({sid}): human_score is blank")
        elif score not in VALID_SCORES:
            errors.append(f"Row {i} ({sid}): human_score is '{score}', must be one of {VALID_SCORES}")

        if not reasoning:
            errors.append(f"Row {i} ({sid}): human_reasoning is blank")

    missing_ids = expected_ids - seen_ids
    if missing_ids:
        errors.append(f"Missing {len(missing_ids)} scenario(s) entirely: {sorted(missing_ids)}")

    if errors:
        print(f"Found {len(errors)} problem(s). Nothing written -- fix these in the CSV and re-run:\n")
        for e in errors:
            print(f"  - {e}")
        return

    with open(OUTPUT, "w") as out:
        for row in rows:
            out.write(json.dumps({
                "scenario_id": row["scenario_id"].strip(),
                "human_score": row["human_score"].strip(),
                "human_reasoning": row["human_reasoning"].strip(),
            }) + "\n")

    print(f"Wrote {len(rows)} validated labels to {OUTPUT}")


if __name__ == "__main__":
    main()
