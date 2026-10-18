# 2026-10-18 single explicitly requested retry

Baseline 9d27143362f7e9cdb7bc1295c3724df160c13b46, project01, initially clean.
The user explicitly requested another attempt. Preliminary read-only Windows power
API returned AC=1, battery=100%; this does not substitute for runtime checks.

Only O3/s24, n4096/random/input seed20261008, one warmup plus five fresh samples.
Frozen measurement content 35a60b090b728d2ec3b6a8ea014beac69fe3766d and validation
session 9332ead2881a4c1e91b966e90a0d2057 remain unchanged. Preserve accepted s128/s64,
original 12-record byte prefix, all historical claims, failures, Grid, and checkpoints.
No Random/Greedy, additional configurations, Grid, n17, or global system changes.

Previously charged 1261.0861871s includes the AC refusal; only 2338.9138129s remain
of the original 3600s. A new exclusive retry-v3 claim binds the entire closed chain.
The new auxiliary helper must be committed and exported exactly before execution.
Only related controlled regressions, no repeat of historical full suites.

Order: formal preflight (original policy), one fresh short/long RAW-QPC attachment,
source/compiler/cache verification without setup, per-group formal gate, fresh
before check, six fresh targets, fresh after check, original accept. Stop and preserve
on any failure, timeout, power event, or exhausted allowance. No automatic retry.
Temporary sleep request released in finally; no promise to prevent lid closure.
Budget is a sum of independent QPC durations, never cross-epoch endpoint subtraction.
Progress every ~60s. Independent postprocessing must separate unexecuted/refused/
passed phases, validation completion, and still-unexecuted P3 search comparison.
