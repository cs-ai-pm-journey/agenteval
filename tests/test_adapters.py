from agenteval.adapters.http import HTTPAdapter
from agenteval.scenario import Scenario


def test_http_adapter_returns_valid_response():
    scenario = Scenario(
        id="test-001",
        input={"text": "my app keeps crashing on startup"},
        expected_output={"category": "bug"},
        case_type="normal",
        labeling_rationale="Crash reports are unambiguous bug reports by definition.",
    )

    adapter = HTTPAdapter(endpoint="http://localhost:8001/classify")
    response = adapter.evaluate(scenario)

    assert response.output["category"] == "bug"
    assert response.confidence == 0.9
    assert response.latency_ms is not None