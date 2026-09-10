"""Validate the LLM judge against independent human labels.

Compares results/block8/judge_scores.jsonl against results/block8/human_labels.jsonl:
  - overall Cohen's kappa (3-class: pass/partial/fail)
  - confusion matrix (judge rows, human columns)
  - per-case-type raw agreement (kappa is not meaningful at n=6-22 per type,
    so this reports agreement rate + disagreement direction instead)
  - each individual disagreement, with both sides' reasoning, for manual review

Writes:
  - docs/judge_validation_report.md (the write-up)
  - results/block8/disagreements.jsonl (every case where judge != human, full detail)
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agenteval.kappa import cohen_kappa, confusion_matrix

ROOT = Path(__file__).resolve().parent.parent
JUDGE_SCORES = ROOT / "results" / "block8" / "judge_scores.jsonl"
HUMAN_LABELS = ROOT / "results" / "block8" / "human_labels.jsonl"
GOLDEN_SET = ROOT / "golden_sets" / "block_8_copilot" / "v1.jsonl"
REPORT_OUT = ROOT / "docs" / "judge_validation_report.md"
DISAGREEMENTS_OUT = ROOT / "results" / "block8" / "disagreements.jsonl"

LABELS = ["pass", "partial", "fail"]

KAPPA_BENCHMARKS = [
    (0.81, "almost perfect"),
    (0.61, "substantial"),
    (0.41, "moderate"),
    (0.21, "fair"),
    (0.00, "slight"),
    (float("-inf"), "poor / no better than chance"),
]


def interpret_kappa(k: float) -> str:
    for threshold, label in KAPPA_BENCHMARKS:
        if k >= threshold:
            return label
    return "poor / no better than chance"


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    judge_rows = {r["scenario_id"]: r for r in load_jsonl(JUDGE_SCORES)}
    human_rows = {r["scenario_id"]: r for r in load_jsonl(HUMAN_LABELS)}
    golden = {r["id"]: r for r in load_jsonl(GOLDEN_SET)}

    missing_judge = set(human_rows) - set(judge_rows)
    missing_human = set(judge_rows) - set(human_rows)
    if missing_judge or missing_human:
        print("WARNING: scenario sets don't fully match.")
        if missing_judge:
            print(f"  In human labels but not judge scores: {sorted(missing_judge)}")
        if missing_human:
            print(f"  In judge scores but not human labels: {sorted(missing_human)}")

    common_ids = sorted(set(judge_rows) & set(human_rows))
    n = len(common_ids)

    judge_scores = [judge_rows[sid]["judge_score"] for sid in common_ids]
    human_scores = [human_rows[sid]["human_score"] for sid in common_ids]

    kappa = cohen_kappa(judge_scores, human_scores, LABELS)
    cm = confusion_matrix(judge_scores, human_scores, LABELS)
    raw_agreement = sum(1 for j, h in zip(judge_scores, human_scores) if j == h) / n

    # Per case_type breakdown
    by_type = {}
    for sid in common_ids:
        ct = judge_rows[sid].get("case_type") or golden.get(sid, {}).get("case_type", "unknown")
        by_type.setdefault(ct, {"n": 0, "agree": 0, "judge_more_lenient": 0, "judge_more_strict": 0})
        j, h = judge_rows[sid]["judge_score"], human_rows[sid]["human_score"]
        by_type[ct]["n"] += 1
        if j == h:
            by_type[ct]["agree"] += 1
        else:
            rank = {"fail": 0, "partial": 1, "pass": 2}
            if rank[j] > rank[h]:
                by_type[ct]["judge_more_lenient"] += 1
            else:
                by_type[ct]["judge_more_strict"] += 1

    # Disagreements, full detail
    disagreements = []
    for sid in common_ids:
        j, h = judge_rows[sid]["judge_score"], human_rows[sid]["human_score"]
        if j != h:
            disagreements.append({
                "scenario_id": sid,
                "case_type": judge_rows[sid].get("case_type") or golden.get(sid, {}).get("case_type"),
                "judge_score": j,
                "judge_reasoning": judge_rows[sid]["judge_reasoning"],
                "human_score": h,
                "human_reasoning": human_rows[sid]["human_reasoning"],
                "direction": "judge_more_lenient" if {"fail": 0, "partial": 1, "pass": 2}[j] >
                             {"fail": 0, "partial": 1, "pass": 2}[h] else "judge_more_strict",
            })

    with open(DISAGREEMENTS_OUT, "w") as f:
        for d in disagreements:
            f.write(json.dumps(d) + "\n")

    # --- console summary ---
    print(f"n = {n}")
    print(f"Raw agreement: {raw_agreement:.1%}")
    print(f"Cohen's kappa: {kappa:.3f} ({interpret_kappa(kappa)})")
    print()
    print("Confusion matrix (rows=judge, cols=human):")
    header = "judge\\human".ljust(12) + "".join(l.ljust(10) for l in LABELS)
    print(header)
    for la in LABELS:
        print(la.ljust(12) + "".join(str(cm[la][lb]).ljust(10) for lb in LABELS))
    print()
    print("Per case_type:")
    for ct, stats in sorted(by_type.items()):
        agree_pct = stats["agree"] / stats["n"] if stats["n"] else 0
        print(f"  {ct}: {stats['agree']}/{stats['n']} agree ({agree_pct:.0%}), "
              f"judge_more_lenient={stats['judge_more_lenient']}, "
              f"judge_more_strict={stats['judge_more_strict']}")
    print()
    print(f"{len(disagreements)} disagreement(s) written to {DISAGREEMENTS_OUT}")

    # --- report ---
    lenient_total = sum(d["direction"] == "judge_more_lenient" for d in disagreements)
    strict_total = sum(d["direction"] == "judge_more_strict" for d in disagreements)

    lines = []
    lines.append("# Judge Validation Report\n")
    lines.append(f"Comparison of `judge_scores.jsonl` (Claude Sonnet, cross-model) against "
                 f"`human_labels.jsonl` (independent human read) across all {n} Block 8 coverage cases.\n")
    lines.append("## Headline numbers\n")
    lines.append(f"- Raw agreement: {raw_agreement:.1%} ({n - len(disagreements)}/{n})")
    lines.append(f"- Cohen's kappa: {kappa:.3f} -- {interpret_kappa(kappa)} agreement, "
                 f"correcting for the agreement chance alone would produce given each rater's own "
                 f"score distribution.")
    lines.append(f"- Disagreements: {len(disagreements)} total -- {lenient_total} where the judge "
                 f"scored more favorably than the human, {strict_total} where the judge scored more "
                 f"harshly.\n")
    lines.append("## Confusion matrix (rows = judge, columns = human)\n")
    lines.append("| judge \\ human | " + " | ".join(LABELS) + " |")
    lines.append("|---|" + "---|" * len(LABELS))
    for la in LABELS:
        lines.append(f"| {la} | " + " | ".join(str(cm[la][lb]) for lb in LABELS) + " |")
    lines.append("")
    lines.append("## Per case_type\n")
    lines.append("| case_type | n | agreement | judge more lenient | judge more strict |")
    lines.append("|---|---|---|---|---|")
    for ct, stats in sorted(by_type.items()):
        agree_pct = stats["agree"] / stats["n"] if stats["n"] else 0
        lines.append(f"| {ct} | {stats['n']} | {stats['agree']}/{stats['n']} ({agree_pct:.0%}) | "
                     f"{stats['judge_more_lenient']} | {stats['judge_more_strict']} |")
    lines.append("")
    if disagreements:
        lines.append("## Disagreements in detail\n")
        for d in disagreements:
            lines.append(f"**{d['scenario_id']}** ({d['case_type']}) -- "
                         f"judge: `{d['judge_score']}`, human: `{d['human_score']}`\n")
            lines.append(f"- Judge's reasoning: {d['judge_reasoning']}")
            lines.append(f"- Human's reasoning: {d['human_reasoning']}\n")
    else:
        lines.append("## Disagreements\n\nNone -- judge and human scores matched on every case.\n")

    REPORT_OUT.parent.mkdir(exist_ok=True)
    with open(REPORT_OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nReport written to {REPORT_OUT}")


if __name__ == "__main__":
    main()
