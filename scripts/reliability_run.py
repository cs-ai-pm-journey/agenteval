"""Reliability run: the pass^k reliability subset (ambiguous + should-abstain +
multi-intent, 28 cases) at k=8 against the live Block 8 Copilot deployment.
Costs real money (~224 GPT-4o pipeline calls) and takes real time
(~18 min at the ~4.8s/call pace from the coverage run).
Run manually with:
    uv run python scripts/reliability_run.py
"""

import json
import time
from datetime import date

import requests

from agenteval.adapters.copilot import BlockEightCopilotAdapter
from agenteval.core import (
    load_golden_set, filter_reliability_subset, run_reliability,
    reliability_report, format_pct_ci,
)

GOLDEN_SET_PATH = "golden_sets/block_8_copilot/v1.jsonl"
ENDPOINT = "https://smart-reply-copilot.onrender.com/api/process"
K = 8

scenarios = load_golden_set(GOLDEN_SET_PATH)
subset = filter_reliability_subset(scenarios)
adapter = BlockEightCopilotAdapter(endpoint=ENDPOINT, timeout=60.0)

print("Warming up Render free-tier instance (skips fast if already warm)...")
try:
    requests.post(ENDPOINT, json={"ticketText": "warmup"}, timeout=90.0)
except requests.exceptions.RequestException as exc:
    print(f"Warm-up call failed ({exc}) -- proceeding anyway.\n")

print(f"Running {len(subset)} scenarios x k={K} = {len(subset) * K} calls against {ENDPOINT}...\n")

start = time.time()
results_by_scenario = run_reliability(adapter, subset, k=K)
duration_seconds = time.time() - start

rel = reliability_report(results_by_scenario)

print(f"\n{'=' * 60}")
print(f"RELIABILITY (pass^{K}): {format_pct_ci(rel, key='pass_k_rate')}  (n_scenarios={rel['n_scenarios']})")
print(f"Duration: {duration_seconds:.0f}s ({duration_seconds / 60:.1f} min)")
print(f"{'=' * 60}\n")

case_type_by_id = {s.id: s.case_type.value for s in subset}
flaky = []
for scenario_id, stats in sorted(rel["per_scenario"].items(), key=lambda kv: kv[1]["pass_rate"]):
    status = "STABLE-PASS" if stats["pass_k"] else ("FLAKY" if stats["successes"] > 0 else "STABLE-FAIL")
    if status == "FLAKY":
        flaky.append(scenario_id)
    print(f"[{status}] {scenario_id} ({case_type_by_id.get(scenario_id)}): {stats['successes']}/{stats['k']} passed")

print(f"\nFlaky scenarios (inconsistent across {K} runs): {len(flaky)}")
for sid in flaky:
    print(f"  {sid}")

output_path = f"results/block8/reliability_{date.today().isoformat()}.json"
with open(output_path, "w") as f:
    json.dump({
        "run_id": f"reliability-{date.today().isoformat()}",
        "adapter": "BlockEightCopilotAdapter",
        "endpoint": ENDPOINT,
        "golden_set_version": "v1",
        "k": K,
        "n_scenarios": rel["n_scenarios"],
        "pass_k_rate": rel["pass_k_rate"],
        "ci_95": [rel["ci_low"], rel["ci_high"]],
        "flaky_scenario_ids": flaky,
        "duration_seconds": duration_seconds,
        "per_scenario": rel["per_scenario"],
    }, f, indent=2)

print(f"\nSaved to {output_path}")
