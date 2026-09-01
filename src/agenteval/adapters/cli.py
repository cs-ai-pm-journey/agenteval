import json
import subprocess
import time

from agenteval.adapters.base import AgentAdapter
from agenteval.scenario import AgentResponse, Scenario


class CLIAdapter(AgentAdapter):
    def __init__(self, command: list[str], timeout: float = 30.0):
        self.command = command  # e.g. [sys.executable, "path/to/agent.py"]
        self.timeout = timeout

    def evaluate(self, scenario: Scenario) -> AgentResponse:
        start = time.time()
        result = subprocess.run(
            self.command,
            input=json.dumps(scenario.input),
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        latency_ms = (time.time() - start) * 1000

        if result.returncode != 0:
            raise RuntimeError(f"Agent CLI failed: {result.stderr}")

        data = json.loads(result.stdout)
        return AgentResponse(
            output=data.get("output", {}),
            confidence=data.get("confidence"),
            metadata=data.get("metadata", {}),
            latency_ms=latency_ms,
        )