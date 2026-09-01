import time

import requests

from agenteval.adapters.http import HTTPAdapter
from agenteval.scenario import AgentResponse, Scenario


class BlockEightCopilotAdapter(HTTPAdapter):
    """Adapter for the Block 8 Smart Reply Copilot.

    Translates between agenteval's Scenario/AgentResponse contract and
    Copilot's native POST /api/process request/response shape:
        request:  {"ticketText": "..."}
        response: {"classification": {...}, "tone": {...},
                   "response": {...}, "overallConfidence": float}
    """

    def evaluate(self, scenario: Scenario) -> AgentResponse:
        copilot_request = {"ticketText": scenario.input.get("text", "")}

        start = time.time()
        response = requests.post(self.endpoint, json=copilot_request, timeout=self.timeout)
        response.raise_for_status()
        latency_ms = (time.time() - start) * 1000

        data = response.json()
        classification = data.get("classification", {})
        tone = data.get("tone", {})
        draft = data.get("response", {})

        return AgentResponse(
            output={
                "category": classification.get("category"),
                "tone": tone.get("type"),
                "urgency": tone.get("urgency"),
            },
            confidence=data.get("overallConfidence"),
            metadata={
                "classification_reasoning": classification.get("reasoning"),
                "classification_confidence": classification.get("confidence"),
                "tone_confidence": tone.get("confidence"),
                "response_draft": draft.get("draft"),
                "response_confidence": draft.get("confidence"),
                "raw_response": data,
            },
            latency_ms=latency_ms,
        )