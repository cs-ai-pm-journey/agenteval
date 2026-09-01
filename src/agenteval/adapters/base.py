from abc import ABC, abstractmethod

from agenteval.scenario import Scenario, AgentResponse


class AgentAdapter(ABC):
    """Base interface every agent adapter must implement.

    An adapter's job is to translate between agenteval's standard
    Scenario/AgentResponse contract and whatever transport or format
    the underlying agent actually speaks (HTTP, CLI, etc.).
    """

    @abstractmethod
    def evaluate(self, scenario: Scenario) -> AgentResponse:
        """Run one scenario against the agent and return its response."""
        ...