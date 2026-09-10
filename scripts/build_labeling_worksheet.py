"""Build a single CSV worksheet for human labeling of the 50 Block 8 coverage cases.

Joins golden_sets/block_8_copilot/v1.jsonl (input, expected_output,
labeling_rationale) with results/block8/coverage_2026-09-02.json (what
Copilot actually output) into one row per scenario, so labeling doesn't
require cross-referencing three separate JSON files by hand.

Deliberately does NOT include the judge's score -- this worksheet is for an
independent human read, and seeing the judge's answer first would defeat the
point of Wednesday's agreement check.

Output: results/block8/labeling_worksheet.csv
Columns: scenario_id, case_type, input_text, expected_output,
         labeling_rationale, actual_output, human_score, human_reasoning

human_score and human_reasoning are left blank for you to fill in.
human_score must be exactly one of: pass, partial, fail
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SET = ROOT / "golden_sets" / "block_8_copilot" / "v1.jsonl"
COVERAGE_RUN = ROOT / "results" / "block8" / "coverage_2026-09-02.json"
OUTPUT = ROOT / "results" / "block8" / "labeling_worksheet.csv"


def load_golden_set(path):
    scenarios = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                scenarios[row["id"]] = row
    return scenarios


def load_coverage_results(path):
    with open(path) as f:
        data = json.load(f)
    return data["individual_results"]


def main():
    golden = load_golden_set(GOLDEN_SET)
    coverage_results = load_coverage_results(COVERAGE_RUN)

    rows = []
    for result in coverage_results:
        scenario_id = result["scenario_id"]
        gs = golden.get(scenario_id)
        if gs is None:
            print(f"WARNING: {scenario_id} not found in golden set, skipping")
            continue
        rows.append({
            "scenario_id": scenario_id,
            "case_type": gs["case_type"],
            "input_text": gs["input"]["text"],
            "expected_output": json.dumps(gs["expected_output"]),
            "labeling_rationale": gs["labeling_rationale"],
            "actual_output": json.dumps(result["actual"]),
            "human_score": "",
            "human_reasoning": "",
        })

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "scenario_id", "case_type", "input_text", "expected_output",
            "labeling_rationale", "actual_output", "human_score", "human_reasoning",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT}")
    print("Fill in human_score (pass / partial / fail) and human_reasoning for each row.")
    print("Then run scripts/finalize_human_labels.py to convert it into results/block8/human_labels.jsonl")


if __name__ == "__main__":
    main()
