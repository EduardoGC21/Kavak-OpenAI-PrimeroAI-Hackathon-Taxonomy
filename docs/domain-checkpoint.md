# Domain implementation checkpoint

The goal is a small reusable baseline, not hand-solving listings. No ASIN
exceptions, source-label gold, threshold tuning, performance claims or model
fine-tuning are part of this change. Exploratory examples and synthetic
expectations remain separate from future held-out human evaluation.

Completed and verified before domain imports: clothing adapter/pack, three code
and three agentic proposals, current source lineage/preservation checks,
64-row offline construction, actual placer-rule tool, and fragrance baseline
engineering suite (25 passed, five data-dependent adapter checks skipped).
The current clothing/footwear paths, schemas, counts and hashes are recorded in
`docs/evidence/clothing-readiness.json`. The mounted RAW root had no separate
toys file at inspection; the mixed games source must be screened separately.
Style/set numerals survive; brands never come from sellers, characters or
compatibility targets. Rules remain proposals/shadow; no human gold is invented.

Completed domain commits imported locally: games `459c07f` and toys `827e37e`.
Their domain-local reports are retained. Shared partition/candidate-facts wiring
is a checkpoint implementation pending combined verification. Shared registry,
fragrance-specific evaluation guards, admitted-only agentic prompts and the
stale `apply_all` repair are implemented. Combined runnable readiness must be
reported only after its checks pass.

Pending at the first draft checkpoint: combined offline verification, toys local
check resolution, final shared run/artifact logging inventory, and updated
integration documentation. Full taxonomy/model runs and human gold evaluation
remain for afterward.

The first-checkpoint pending implementation items are now complete: both domain
commits are imported unchanged, shared hooks/checks are connected, combined
offline checks pass, and construction writes success/failure manifests and
structured artifact logs. See `docs/evidence/domain-integration.json` and
`docs/new-domain-harness.md`. Full taxonomy, human gold and model-run trace
collection remain later work. The draft PR stays unmerged for coordinator review.

Future distillation requires reviewable evidence -> candidate alternatives ->
decision/abstention -> validator or human outcome -> rule/prompt change, with
counterexamples and regressions. Save structured outputs and tool traces, not
hidden reasoning. Calls not made have no traces or token/cost measurements.
Full data-bearing artifacts stay outside Git; scripts and hash-indexed summaries
may be committed. Logging that is implemented versus still required is documented
in the final shared integration note; this checkpoint is not a training system.
