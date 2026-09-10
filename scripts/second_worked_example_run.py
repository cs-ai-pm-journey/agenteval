"""Run agenteval against the expense_router example -- the second worked
example proving the harness generalizes beyond Block 8 Copilot.

Differences from the Copilot run, deliberately:
  - CLIAdapter (stdin/stdout), not HTTPAdapter
  - the agent speaks agenteval's native contract directly -- no translating
    adapter subclass needed, unlike BlockEightCopilotAdapter
  - a deterministic rule-based agent, not an LLM -- so pass^k is run too,
    to demonstrate (not just assert) that a non-LLM agent is perfectly
    stable across repeated runs

Writes results/expense_router/coverage_<date>.json and
results/expense_router/reliability_<date>.json.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agenteval.adapters.cli import CLIAdapter
from agenteval.core import (
    load_golden_set, run_coverage, run_reliability,
    filter_reliability_subset, pass_k_result, wilson_ci,
)

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SET = ROOT / "golden_sets" / "expense_router" / "v1.jsonl"
AGENT_SCRIPT = ROOT / "examples" / "expense_router" / "agent.py"
RESULTS_DIR = ROOT / "results" / "expense_router"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    scenarios = load_golden_set(str(GOLDEN_SET))
    adapter = CLIAdapter(command=[sys.executable, str(AGENT_SCRIPT)])

    # --- Coverage (pass@1) ---
    results = run_coverage(adapter, scenarios)
    passed = sum(1 for r in results if r.passed)
    n = len(results)
    ci = wilson_ci(passed, n)

    by_type = {}
    for scenario, result in zip(scenarios, results):
        ct = scenario.case_type.value
        by_type.setdefault(ct, {"passed": 0, "n": 0})
        by_type[ct]["n"] += 1
        if result.passed:
            by_type[ct]["passed"] += 1

    by_type_report = {}
    for ct, stats in by_type.items():
        ct_ci = wilson_ci(stats["passed"], stats["n"])
        by_type_report[ct] = {
            "pass_rate": stats["passed"] / stats["n"],
            "ci_95": list(ct_ci),
            "n": stats["n"],
        }

    coverage_out = {
        "run_id": f"expense-router-coverage-{today}",
        "adapter": "CLIAdapter (expense_router/agent.py)",
        "golden_set_version": "v1",
        "total_scenarios": n,
        "results_summary": {
            "pass_rate": passed / n,
            "ci_95": list(ci),
            "by_case_type": by_type_report,
        },
        "individual_results": [
            {
                "scenario_id": s.id,
                "case_type": s.case_type.value,
                "passed": r.passed,
                "expected": s.expected_output,
                "actual": r.agent_response.output,
                "confidence": r.agent_response.confidence,
            }
            for s, r in zip(scenarios, results)
        ],
    }
    coverage_path = RESULTS_DIR / f"coverage_{today}.json"
    with open(coverage_path, "w") as f:
        json.dump(coverage_out, f, indent=2)

    print(f"Coverage: {passed}/{n} = {passed/n:.1%} (95% CI: {ci[0]:.1%}-{ci[1]:.1%})")
    for ct, stats in sorted(by_type_report.items()):
        print(f"  {ct}: {stats['pass_rate']:.0%} (n={stats['n']})")
    print(f"Written to {coverage_path}")

    # --- Reliability (pass^k) on the reliability_subset, k=8 ---
    subset = filter_reliability_subset(scenarios)
    results_by_scenario = run_reliability(adapter, subset, k=8)

    stable_pass = stable_fail = flaky = 0
    per_scenario = []
    for scenario in subset:
        runs = results_by_scenario[scenario.id]
        outcomes = [r.passed for r in runs]
        n_passed = sum(outcomes)
        if n_passed == len(outcomes):
            stable_pass += 1
        elif n_passed == 0:
            stable_fail += 1
        else:
            flaky += 1
        per_scenario.append({
            "scenario_id": scenario.id,
            "case_type": scenario.case_type.value,
            "k": len(outcomes),
            "n_passed": n_passed,
            "pass_k": pass_k_result(runs),
        })

    reliability_out = {
        "run_id": f"expense-router-reliability-{today}",
        "k": 8,
        "n_scenarios": len(subset),
        "stable_pass": stable_pass,
        "stable_fail": stable_fail,
        "flaky": flaky,
        "per_scenario": per_scenario,
    }
    reliability_path = RESULTS_DIR / f"reliability_{today}.json"
    with open(reliability_path, "w") as f:
        json.dump(reliability_out, f, indent=2)

    print()
    print(f"Reliability (k=8, n={len(subset)}): stable_pass={stable_pass}, "
          f"stable_fail={stable_fail}, flaky={flaky}")
    print(f"Written to {reliability_path}")


if __name__ == "__main__":
    main()
