#!/usr/bin/env python3
"""A small, deterministic expense-report categorizer.

Not an LLM -- a rule-based CLI agent, on purpose. It exists to prove
agenteval's adapter contract generalizes beyond Block 8 Copilot: a
completely different domain (expense categorization vs. support-ticket
routing), a completely different transport (CLI stdin/stdout vs. HTTP),
and -- unlike Copilot -- an agent that *was* built with an explicit
abstain path and a pre-classifier policy gate, the exact fix recommended
for Copilot in docs/block8_analysis.md's "What I'd Change" section.

Speaks agenteval's native CLI contract directly: reads {"text": ...} as
JSON on stdin, writes {"output": {...}, "confidence": ..., "metadata": {...}}
as JSON to stdout. No translating adapter needed -- CLIAdapter works
against it unmodified.

Categories: Travel, Meals & Entertainment, Software & Subscriptions,
Office Supplies, Equipment, or Needs Human Review (the abstain category).
"""
import json
import re
import sys

POLICY_REVIEW_THRESHOLD_USD = 5000

INJECTION_MARKERS = [
    "ignore", "disregard", "override", "regardless of policy",
    "regardless of the rules", "just approve", "skip review",
]

CATEGORY_KEYWORDS = [
    # (category, keywords) -- checked in this order; first match wins.
    ("Travel", ["flight", "airfare", "hotel", "uber", "lyft", "taxi",
                "rental car", "train ticket", "mileage", "airport"]),
    ("Software & Subscriptions", ["subscription", "software license",
                                   "saas", "monthly plan", "api credits",
                                   "cloud hosting"]),
    ("Equipment", ["laptop", "monitor", "keyboard", "webcam", "docking station",
                   "external hard drive"]),
    ("Meals & Entertainment", ["restaurant", "lunch", "dinner", "coffee",
                                "client meal", "team lunch", "catering"]),
    ("Office Supplies", ["pens", "notebook", "stapler", "paper", "supplies",
                          "printer ink"]),
]


def extract_amount(text: str) -> float | None:
    # Require the literal $ immediately before the digits -- a bare
    # "[\d,]+" is too permissive and can match a stray comma elsewhere
    # in the sentence (e.g. "Chicago, $9,500" without the $ anchor), which
    # silently fails to parse and lets amounts slip past the review gate.
    match = re.search(r"\$([\d,]+(?:\.\d{2})?)", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def classify(text: str) -> tuple[str, float]:
    lowered = text.lower().strip()

    if not lowered:
        return "Needs Human Review", 0.99

    if any(marker in lowered for marker in INJECTION_MARKERS):
        return "Needs Human Review", 0.97

    amount = extract_amount(lowered)
    if amount is not None and amount >= POLICY_REVIEW_THRESHOLD_USD:
        return "Needs Human Review", 0.95

    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return category, 0.85

    return "Needs Human Review", 0.6


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    text = payload.get("text", "")

    category, confidence = classify(text)

    result = {
        "output": {"category": category},
        "confidence": confidence,
        "metadata": {"agent": "expense_router_stub", "rule_based": True},
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
