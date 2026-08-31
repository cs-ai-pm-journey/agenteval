"""Core data models for agenteval.

These Pydantic models define the language-agnostic contract between the
evaluation harness and any agent under test. Agents communicate over HTTP
or CLI (never in-process), and must produce responses matching AgentResponse.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CaseType(str, Enum):
    """Classification of golden-set scenarios by purpose.
    
    Different case types serve different measurement goals:
    - NORMAL: baseline capability coverage
    - AMBIGUOUS: tests boundary judgment and overconfidence
    - SHOULD_ABSTAIN: tests knowing-when-not-to-answer (highest signal)
    - ADVERSARIAL: tests robustness against prompt injection
    - MULTI_INTENT: tests handling of real-world messy inputs
    """
    NORMAL = "normal"
    AMBIGUOUS = "ambiguous"
    SHOULD_ABSTAIN = "should_abstain"
    ADVERSARIAL = "adversarial"
    MULTI_INTENT = "multi_intent"


class Scenario(BaseModel):
    """A single test case in a golden set.
    
    Every scenario requires a labeling rationale explaining WHY the expected
    output is correct. This rationale defends the ground truth during judge
    validation and provides interviewer-ready receipts for label decisions.
    """
    id: str
    input: dict  # Flexible payload — shape depends on the agent's contract
    expected_output: dict
    case_type: CaseType
    labeling_rationale: str = Field(
        ...,
        min_length=20,
        description="Explanation of why the expected output is correct",
    )
    tags: list[str] = Field(default_factory=list)
    reliability_subset: bool = Field(
        default=False,
        description="If True, this scenario is included in pass^k reliability runs",
    )


class AgentResponse(BaseModel):
    """The standardized response format returned by any adapter.
    
    Adapters translate between an agent's native response shape and this
    canonical format. All downstream evaluation code operates on this shape,
    never on the raw agent response.
    """
    output: dict
    confidence: Optional[float] = None
    metadata: dict = Field(default_factory=dict)
    latency_ms: Optional[float] = None


class ScenarioResult(BaseModel):
    """The outcome of running one scenario against an agent one time.
    
    For pass@1 (coverage) runs, run_index is always 0.
    For pass^k (reliability) runs, run_index ranges from 0 to k-1.
    """
    scenario_id: str
    passed: bool
    agent_response: AgentResponse
    judge_reasoning: Optional[str] = None
    run_index: int = 0
    cost_usd: Optional[float] = None 