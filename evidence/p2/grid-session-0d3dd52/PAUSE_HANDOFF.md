# P2 Grid pause handoff

Paused at 2026-10-08 19:05:26 +08:00 because the user reported imminent laptop shutdown.

- Content commit: `0d3dd5242c728d8001dd02a4e332185459d04721`
- Session: `d915c261f56a4eeea1e5c0531876d967`
- Protocol identity hash: `2b1a75e9c5f88b80d83a47be4e34c2c5577d82d1468f37fd976e0d6d6ce5b828`
- Complete configurations: 1 (`O0`, block size 8), safely reusable from all six raw samples.
- Interrupted configuration: `O0`, block size 16, attempt
  `2b7e1cedf6544165a24d0b5e9b75404a`.
- Retained partial evidence: three successful executions (warmup and two measurements).
- Required resume behavior: move the active attempt to `abandoned/`, then restart this
  configuration with a new warmup and five new measurements. Do not combine partial samples.
- Target and Grid runner processes were absent after stopping.
- Clean content export, Git identity, session/protocol manifests and cached reference were present.

Resume from WSL after restoring power and allowing resource gates to pass:

```bash
cd /var/tmp/matrix-autotuner-p2-content-0d3dd5242c728d8001dd02a4e332185459d04721
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner grid \
  --content-sha 0d3dd5242c728d8001dd02a4e332185459d04721 \
  --git-identity /mnt/e/software_system/project01/build/p2/git_identity.json \
  --session-directory /mnt/e/software_system/project01/evidence/p2/grid-session-0d3dd52 \
  --resume
```

If WSL local files were removed by an external cleanup, first recreate only the content export
with `scripts/prepare_p2_content.ps1`. The reference cache is identity-checked; if absent it will
be regenerated rather than replaced with historical performance data.
