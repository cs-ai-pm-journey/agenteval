"""Manual smoke test for BlockEightCopilotAdapter against the live Render
deployment. NOT part of the pytest suite — this hits a real GPT-4o pipeline
and costs money on every run. Run manually with:
    uv run python scripts/smoke_test_copilot.py
"""

from agenteval.adapters.copilot import BlockEightCopilotAdapter
from agenteval.scenario import Scenario

adapter = BlockEightCopilotAdapter(
    endpoint="https://smart-reply-copilot.onrender.com/api/process",
    timeout=30.0,
)

scenario = Scenario(
    id="copilot-smoke-001",
    input={"text": "My app keeps crashing when I try to export data."},
    expected_output={"category": "Bug Report"},
    case_type="normal",
    labeling_rationale="A reproducible app crash is unambiguously a bug report.",
)

response = adapter.evaluate(scenario)
print(response)
assert response.output["category"] == scenario.expected_output["category"], "Category mismatch!"
print(f"\nPASS — latency: {response.latency_ms:.0f}ms, confidence: {response.confidence:.3f}")