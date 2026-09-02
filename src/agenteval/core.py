import json

from agenteval.adapters.base import AgentAdapter
from agenteval.scenario import Scenario, ScenarioResult


def load_golden_set(path: str) -> list[Scenario]:
    scenarios = []
    with open(path) as f:
        for line in f:
            if line.strip():
                scenarios.append(Scenario.model_validate_json(line))
    return scenarios


def simple_match(actual: dict, expected: dict) -> bool:
    """Basic dict matching -- checks all expected keys/values exist in actual."""
    for key, value in expected.items():
        if actual.get(key) != value:
            return False
    return True


def run_coverage(adapter: AgentAdapter, scenarios: list[Scenario]) -> list[ScenarioResult]:
    results = []
    for scenario in scenarios:
        response = adapter.evaluate(scenario)
        passed = simple_match(response.output, scenario.expected_output)
        results.append(ScenarioResult(
            scenario_id=scenario.id,
            passed=passed,
            agent_response=response,
            run_index=0,
        ))
    return results

def run_reliability(
    adapter: AgentAdapter,
    scenarios: list[Scenario],
    k: int = 8,
) -> dict[str, list[ScenarioResult]]:
    """Run each scenario k times. Returns dict of scenario_id -> list of results."""
    results_by_scenario = {}
    for scenario in scenarios:
        runs = []
        for i in range(k):
            response = adapter.evaluate(scenario)
            passed = simple_match(response.output, scenario.expected_output)
            runs.append(ScenarioResult(
                scenario_id=scenario.id,
                passed=passed,
                agent_response=response,
                run_index=i,
            ))
        results_by_scenario[scenario.id] = runs
    return results_by_scenario


def pass_k_result(runs: list[ScenarioResult]) -> bool:
    """A scenario passes pass^k only if ALL k runs passed."""
    return all(r.passed for r in runs)


def filter_reliability_subset(scenarios: list[Scenario]) -> list[Scenario]:
    return [s for s in scenarios if s.reliability_subset]


def wilson_ci(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. Returns (low, high) as fractions.

    Standard method for expressing pass-rate uncertainty on small samples --
    a bare "94%" on 50 cases hides that the true rate could plausibly be
    anywhere from the low 80s to high 90s.
    """
    from statsmodels.stats.proportion import proportion_confint

    if n == 0:
        return (0.0, 0.0)
    low, high = proportion_confint(successes, n, alpha=alpha, method="wilson")
    return (low, high)


def coverage_report(results: list[ScenarioResult]) -> dict:
    """Pass@1 accuracy across a set of results, with a Wilson 95% CI."""
    n = len(results)
    successes = sum(1 for r in results if r.passed)
    accuracy = successes / n if n else 0.0
    low, high = wilson_ci(successes, n)
    return {
        "n": n,
        "successes": successes,
        "accuracy": accuracy,
        "ci_low": low,
        "ci_high": high,
    }


def reliability_report(results_by_scenario: dict[str, list[ScenarioResult]]) -> dict:
    """pass^k success rate across the reliability subset, with a Wilson CI and
    per-scenario variance (each scenario's own pass rate across its k runs,
    to spot which specific cases are unstable rather than just the aggregate)."""
    n = len(results_by_scenario)
    per_scenario = {}
    successes = 0
    for scenario_id, runs in results_by_scenario.items():
        k = len(runs)
        run_successes = sum(1 for r in runs if r.passed)
        all_passed = pass_k_result(runs)
        successes += int(all_passed)
        per_scenario[scenario_id] = {
            "k": k,
            "successes": run_successes,
            "pass_rate": run_successes / k if k else 0.0,
            "pass_k": all_passed,
        }
    pass_k_rate = successes / n if n else 0.0
    low, high = wilson_ci(successes, n)
    return {
        "n_scenarios": n,
        "pass_k_successes": successes,
        "pass_k_rate": pass_k_rate,
        "ci_low": low,
        "ci_high": high,
        "per_scenario": per_scenario,
    }


def coverage_by_case_type(results: list[ScenarioResult], scenarios: list[Scenario]) -> dict:
    """Pass@1 accuracy broken down by case_type, each bucket with its own Wilson CI.
    This is usually more informative than the blended overall number -- a classifier
    can look strong overall while quietly failing every should-abstain case."""
    case_type_by_id = {s.id: s.case_type.value for s in scenarios}
    buckets: dict[str, list[ScenarioResult]] = {}
    for r in results:
        case_type = case_type_by_id.get(r.scenario_id, "unknown")
        buckets.setdefault(case_type, []).append(r)
    return {ct: coverage_report(bucket) for ct, bucket in buckets.items()}


def format_pct_ci(report: dict, key: str = "accuracy") -> str:
    """Human-readable string, e.g. '94.0% (95% CI: 83.0%-98.0%)'."""
    rate = report[key]
    return f"{rate:.1%} (95% CI: {report['ci_low']:.1%}-{report['ci_high']:.1%})"
