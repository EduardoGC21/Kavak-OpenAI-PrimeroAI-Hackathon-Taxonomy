# Evaluation lessons (how improvements turned out fake before)

Read by whoever designs a domain's evaluation. Each lesson keeps the evidence it came from; retire it if it stops
holding.

1. **An LLM judge is not truth.** Methods agreeing with each other is not accuracy. Truth = a person's blind,
   random labels.
2. **A won A/B is not a correct change.** Score changes against labels, not against the previous version.
3. **One held-out read.** Freeze the held-out labels; read them once, after the decision, from code only.
4. **No mutants as evidence.** Planted faults test a check, not the system; real errors omit, mutants add words.
5. **No echo checks.** A check must run and must be able to fail; it is admitted only if it fires on a planted
   fault and stays quiet on a known-good case.
6. **Omission = abstain.** An unexamined candidate is not a "no", and not a "yes" either.
7. **Identifiers never decide alone.** An exact id or alias only proposes a candidate; the context must agree.
