# Judge Validation Report

Comparison of `judge_scores.jsonl` (Claude Sonnet, cross-model) against `human_labels.jsonl` (independent human read) across all 50 Block 8 coverage cases.

## Headline numbers

- Raw agreement: 84.0% (42/50)
- Cohen's kappa: 0.654 -- substantial agreement, correcting for the agreement chance alone would produce given each rater's own score distribution.
- Disagreements: 8 total -- 2 where the judge scored more favorably than the human, 6 where the judge scored more harshly.

## Confusion matrix (rows = judge, columns = human)

| judge \ human | pass | partial | fail |
|---|---|---|---|
| pass | 31 | 1 | 1 |
| partial | 3 | 1 | 0 |
| fail | 2 | 1 | 10 |

## Per case_type

| case_type | n | agreement | judge more lenient | judge more strict |
|---|---|---|---|---|
| ambiguous | 12 | 6/12 (50%) | 2 | 4 |
| multi_intent | 6 | 4/6 (67%) | 0 | 2 |
| normal | 22 | 22/22 (100%) | 0 | 0 |
| should_abstain | 10 | 10/10 (100%) | 0 | 0 |

## Disagreements in detail

**b8-ambig-001** (ambiguous) -- judge: `fail`, human: `partial`

- Judge's reasoning: The expected category is 'Feature Request' since the undo limit is a design tradeoff rather than a defect, but the agent classified it as 'Bug Report', which mismatches the expected field.
- Human's reasoning: I think this would lean more toward the bug report. If this is something we generally wouldn't/don't offer then it could be a feature request.

**b8-ambig-004** (ambiguous) -- judge: `pass`, human: `fail`

- Judge's reasoning: The agent's category field matches the expected 'Billing Issue' exactly. Extra fields (tone, urgency) do not count against the score.
- Human's reasoning: I would put this as a technical support. Customer's main question is where to fin dthe invoice. The last part (which outweighs the other on the reasoning) is just what they need that original for.

**b8-ambig-006** (ambiguous) -- judge: `partial`, human: `pass`

- Judge's reasoning: The expected category is Technical Support since this is a configuration/how-to request, but the agent labeled it Billing Issue. The rationale notes Billing Issue is defensible given the subject matter, so it's not a clear-cut wrong answer but a mismatch from the expected label, warranting partial credit rather than a full fail.
- Human's reasoning: tech support requested

**b8-ambig-008** (ambiguous) -- judge: `partial`, human: `pass`

- Judge's reasoning: The expected category is 'Technical Support' since the core request is about how/where to find a document, though the rationale explicitly acknowledges 'Billing Issue' is defensible given the financial nature of the content. The agent chose 'Billing Issue', which aligns with this acknowledged alternative interpretation, but doesn't match the primary expected label.
- Human's reasoning: Feature request

**b8-ambig-009** (ambiguous) -- judge: `pass`, human: `partial`

- Judge's reasoning: The agent's category field 'Billing Issue' exactly matches the expected output, and extra fields (tone, urgency) are permitted additions that don't count against the score.
- Human's reasoning: This should be tech support/billing issue. They are asking specifically if that is something they can do. Tech support would be my first choice on this then moving to billing.

**b8-ambig-012** (ambiguous) -- judge: `partial`, human: `pass`

- Judge's reasoning: The expected category is 'Technical Support' with a note that 'Billing Issue' is defensible as an alternative interpretation. The agent chose 'Billing Issue', which the rationale explicitly acknowledges as reasonable but not the primary expected answer, so it's a close but not exact match.
- Human's reasoning: tech support requested

**b8-multi-001** (multi_intent) -- judge: `fail`, human: `pass`

- Judge's reasoning: The expected category is 'Technical Support' because the login failure is the dominant, actionable issue, but the agent categorized it as 'Billing Issue', which mismatches the expected field.
- Human's reasoning: tech support requested

**b8-multi-002** (multi_intent) -- judge: `fail`, human: `pass`

- Judge's reasoning: The expected category is 'Bug Report' due to the broken detail panel functionality taking priority, but the agent categorized it as 'Feature Request', missing the primary bug issue.
- Human's reasoning: I agree with the reasoning

