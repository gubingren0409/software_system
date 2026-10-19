# First-seed RAW comparison: declaration before actual experiments

User authorization based on project01/efb7f9df9c25dd509e207d67e08d4180c3e779ac.
Only search seed20261008, Random12 then its deduplicated prefix retests, Greedy12
then its deduplicated prefix retests. B4/8/12 are prefixes, not separate searches.
Each group1 warmup +5 fresh, RAW median, full n4096/random input seed20261008.
Search and matrix seeds are separate fields. No other seeds or algorithms.

Scientific content3cc9e0d, C/input/reference/20 configs/compiler flags/tolerances,
RAW timing and resource policyv2 unchanged. No performance-sample cache reuse.
Only verified build/reference caches may be shared. Each strategy sees only its own
search observations, not validation, Grid, the other algorithm, or independent retests.

Freeze and exactly export a new committed runner; initialize a NEW empty search
session and exact search authorization. No reuse of old empty sessions/certificates.
Completed validation9332ead2 and its18 records, closed Grid, failures and claims
are protected by full file hashes; unused validation1616.5610957s is not transferred.

New claim has43200s host QPC activity budget, including gates, one fresh short/long
RAW admission, setup verification, search, retests, boundary checks and cleanup.
No reset, extra window, failed-group retry, filtering or replacement. Any failure,
standby, invalid clock, resource exhaustion or budget exhaustion stops with evidence.
Evidence volume >=1GiB + actual write/fsync/read-back at start and before each group.
Keep AC connected and lid open; temporary sleep request released in finally.
Formal wait <=120s incl collection/retries. Resource v2 and RAW thresholds unchanged.
Progress about every60s, matrix targets serial; clocks outside target timing.

Success requires24 search groups plus R=2..6 algorithm-internal deduplicated retests,
156..180 unique fresh target executions, two replayable12-configuration trajectories,
six correct prefixes with retest mapping, no unaccepted/extra samples and normally
completed checkpoint/window within budget. All scores/RAW/resource/continuity checks
independently recomputed. Scope explicitly first_seed, NOT five-seed completion.
Controlled fake tests are not measurements. Historical standby Grid is not used to
claim QPC end-to-end speedup. Nested RAW/QPC costs not double-added. Stop after delivery.
