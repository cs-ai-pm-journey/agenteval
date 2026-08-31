# Golden Set Origin

## Recovery Attempt

Searched local machine, Block 8 GitHub repo (https://github.com/cs-ai-pm-journey/Block-8), and Block 8 documentation for the original 22-case golden set built during the Block 8 emergency build.

**Result:** Original golden set not recoverable. Ticket texts and labels could not be located in the Block 8 repo, local files, or supporting documentation.

## Decision

Rebuilding the golden set from scratch for Block 10 rather than attempting further recovery.

## Rationale

The original Block 8 golden set was built during a 4-hour emergency build ahead of a Friday interview. It predated the Block 10 methodology work on:

- pass^k reliability testing (requires deliberate reliability subset selection)
- Should-abstain cases as first-class scenarios (highest-signal cases per golden set design principles)
- Adversarial cases (prompt injection robustness)
- Multi-intent cases (real-world messiness)
- Labeling rationale as a durable artifact (needed for judge validation defense in Week 3)

Even a recovered original set would require migration into the new Pydantic Scenario schema and substantial augmentation to hit the target case-type distribution. Rebuilding from scratch with proper methodology produces a stronger, more defensible dataset than retrofitting the original.

The tradeoff: loses the specific narrative "here's the same 22 cases that scored 95.5% at pass@1, now measured at pass^k." Gained: a properly-designed golden set from case one, with methodology matching measurement claims.

## Target Distribution (Golden Set v1)

| Case Type | Count | Purpose |
|---|---|---|
| Normal | 20 | Coverage baseline; basic capability |
| Ambiguous | 10 | Boundary judgment; overconfidence detection |
| Should-abstain | 8 | Knowing-when-not-to-answer signal |
| Adversarial | 6 | Prompt injection robustness |
| Multi-intent | 6 | Real support ticket messiness |
| **Total** | **50** | |

Construction happens Wednesday (30 cases baseline) through Friday (50 cases complete).