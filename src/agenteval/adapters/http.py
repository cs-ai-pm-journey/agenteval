import time

import requests

from agenteval.adapters.base import AgentAdapter
from agenteval.scenario import AgentResponse, Scenario


class HTTPAdapter(AgentAdapter):
    def __init__(self, endpoint: str, timeout: float = 30.0):
        self.endpoint = endpoint
        self.timeout = timeout

    def evaluate(self, scenario: Scenario) -> AgentResponse:
        start = time.time()
        response = requests.post(
            self.endpoint,
            json=scenario.input,
            timeout=self.timeout,
        )
        response.raise_for_status()
        latency_ms = (time.time() - start) * 1000

        data = response.json()
        return AgentResponse(
            output=data.get("output", {}),
            confidence=data.get("confidence"),
            metadata=data.get("metadata", {}),
            latency_ms=latency_ms,
        )