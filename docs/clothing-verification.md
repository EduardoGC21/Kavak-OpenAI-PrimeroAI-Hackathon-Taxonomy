# Clothing verification protocol

Before implementation, the identified failure modes are: stale or unconfigured input;
manifest hash mismatch; missing/misaligned sidecar; signed identifiers truncated or
replaced with row numbers; duplicate observations or ASINs; lost raw fields;
seller/licensor promoted to maker; graphics routed to toys/games; footwear,
accessories or department-only evidence accepted as garments; text-quality holds
ignored; style numerals and audience/size strings erased; multipacks confused with
coordinated sets; duplicate marketplace pages counted as independent product proof;
missing taxonomy mistaken for a broken adapter or fabricated trusted tree; proposal
or shadow rules affecting decisions; RuleSpec/evaluator status mixing; local check
names failing through the actual placer tool; fragrance gold or vocabulary leaking
into a new domain; unsupported evaluation reading sealed fixtures; output collisions;
and model calls during an offline run.

Verification uses a smoke import/load before bounded offline end-to-end checks.
Synthetic positive/negative cases are engineering expectations, never human gold.
The executable check is `python -m checks.clothing_readiness --help`. Its JSON report
records hashes, counts and assertions without raw payloads. Full source profiling is
separate from the bounded construction check; no full taxonomy run is authorized.
