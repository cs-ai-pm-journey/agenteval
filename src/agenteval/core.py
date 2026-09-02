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
