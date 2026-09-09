"""Run the LLM-as-judge against all real coverage-run responses.

Joins the golden set (input_text, expected_output, labeling_rationale) with
the actual Copilot outputs captured in the coverage run, judges each one,
and writes results/block8/judge_scores.jsonl.

Resumable: skips scenario_ids already present in the output file, so an
interrupted run can just be re-invoked.

One line per scenario:
{scenario_id, judge_score, judge_reasoning, cost_usd, coverage_passed, case_type}
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agenteval.judge import Judge, JudgeParseError

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SET = ROOT / "golden_sets" / "block_8_copilot" / "v1.jsonl"
COVERAGE_RUN = ROOT / "results" / "block8" / "coverage_2026-09-02.json"
OUTPUT = ROOT / "results" / "block8" / "judge_scores.jsonl"


def load_golden_set(path: Path) -> dict[str, dict]:
    scenarios = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                scenarios[row["id"]] = row
    return scenarios


def load_coverage_results(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data["individual_results"]


def load_already_scored(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    with open(path) as f:
        for line in f:
            if line.strip():
                done.add(json.loads(line)["scenario_id"])
    return done


def main():
    golden = load_golden_set(GOLDEN_SET)
    coverage_results = load_coverage_results(COVERAGE_RUN)
    already_scored = load_already_scored(OUTPUT)

    if len(coverage_results) != len(golden):
        print(f"WARNING: coverage run has {len(coverage_results)} results, "
              f"golden set has {len(golden)} scenarios.")
    if already_scored:
        print(f"Resuming: {len(already_scored)} scenarios already scored, skipping those.")

    judge = Judge()
    total_cost = 0.0
    scored = 0
    errors = []

    with open(OUTPUT, "a") as out:
        for i, result in enumerate(coverage_results, 1):
            scenario_id = result["scenario_id"]
            if scenario_id in already_scored:
                continue

            gs = golden.get(scenario_id)
            if gs is None:
                print(f"[{i}/{len(coverage_results)}] SKIP {scenario_id}: not in golden set")
                errors.append(scenario_id)
                continue

            try:
                judgment = judge.judge(
                    input_text=gs["input"]["text"],
                    expected_output=gs["expected_output"],
                    labeling_rationale=gs["labeling_rationale"],
                    actual_output=result["actual"],
                )
            except JudgeParseError as e:
                print(f"[{i}/{len(coverage_results)}] JUDGE PARSE ERROR {scenario_id}: {e}")
                errors.append(scenario_id)
                continue

            total_cost += judgment.cost_usd or 0.0
            scored += 1

            row = {
                "scenario_id": scenario_id,
                "case_type": gs["case_type"],
                "judge_score": judgment.score.value,
                "judge_reasoning": judgment.reasoning,
                "cost_usd": judgment.cost_usd,
                "coverage_passed": result["passed"],
            }
            out.write(json.dumps(row) + "\n")
            out.flush()
            print(f"[{i}/{len(coverage_results)}] {scenario_id} ({gs['case_type']}): "
                  f"judge={judgment.score.value} coverage_passed={result['passed']}")

    print()
    print(f"This run scored {scored} new scenarios. Errors: {len(errors)} {errors if errors else ''}")
    print(f"This run's cost: ${total_cost:.4f}")
    total_done = len(load_already_scored(OUTPUT))
    print(f"Total in {OUTPUT.name}: {total_done}/{len(coverage_results)}")


if __name__ == "__main__":
    main()
