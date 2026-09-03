# What pass@1 hides

Most AI system evaluations report one number: pass rate. Run each test case
once, count how many passed, done. I did that this week on a support-ticket
classifier I built and shipped myself, then did something less common — ran
the same test cases eight times each and only counted a case as passing if
every single run succeeded. Here's what changed, and more importantly, what
didn't.

The system is Block 8 Copilot: it reads a support ticket and routes it to
one of five categories -- Bug Report, Feature Request, Billing Issue,
Technical Support, or General Inquiry. At pass@1 -- one run per test case --
it scored 66% on a 50-case golden set. Broken down by case type, it gets
more interesting: 100% on straightforward tickets, 58% on deliberately
ambiguous boundary cases, 67% on tickets bundling two distinct issues into
one message. And 0% -- zero -- on the ten cases where the correct behavior
was to not confidently answer at all.

Then came the harder test. Every case in the harness's reliability subset --
28 cases: everything ambiguous, everything should-abstain, everything
multi-intent -- ran 8 times each, counted as passing only if it passed all
8. That's pass^k, and it exists to catch a specific lie pass@1 tells: a
system that's right 75% of the time on a given case isn't "mostly
reliable" -- it's a coin flip your users eventually lose.

The expected story here is "pass^k reveals a system that looked fine and
wasn't." That's not quite what happened. pass@1 on this same 28-case subset
was 39%; pass^8 brought it to 36% -- a 3.6-point gap. Small. Twenty-six of
the twenty-eight cases were perfectly deterministic across all 8 runs --
either 8 for 8 or 0 for 8, every time. Only two cases actually flip-flopped.

That's the finding worth sitting with: this system's unreliability isn't
randomness. It's confidence. The should-abstain cases scored 0% not because
the model got unlucky sometimes -- it never once, across 80 total attempts,
declined to answer. A prompt-injection attempt got classified as "Feature
Request" at 93% confidence. A request that used an account-recovery framing
to ask for another user's billing details got labeled "Billing Issue" at
90% confidence. Those confidence scores are statistically indistinguishable
from its confidence on cases it got right.

So pass^k's real value here wasn't exposing hidden flakiness -- there
wasn't much to expose. Its value was diagnostic: it proved these failures
are structural, not statistical. A system that's randomly wrong 30% of the
time might improve with a better model or a few more examples. A system
that's deterministically, confidently wrong on an entire category of input
has a design gap -- in this case, an output schema with no abstain option,
and no code path anywhere upstream of the model that could catch these
before they ever reach it.

pass@1 would have told me "66%, needs work." pass^k told me which 3.6
points were noise, and which 64.3 points of failure were something the
model will never fix on its own, no matter how many times you ask it.
