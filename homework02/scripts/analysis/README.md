# A2 core research reproducibility

The commands below assume `homework02/` as the working directory and Python 3; `plot_core.py` additionally needs NumPy and Matplotlib. The scripts themselves locate project data relative to their own path. They never invoke the formal `.007` benchmark.

1. `python scripts/analysis/build_core_data.py` — parse preserved `.007` raw/txt plus `.008`–`.010` repeats; regenerate the three core CSVs.
2. `python scripts/analysis/verify_official_data.py` — compare the 14 selected official scores with two saved, SHA-256-checked SPEC HTML reports.
3. `python scripts/analysis/plot_core.py` — regenerate four source-driven PNGs.
4. `python scripts/analysis/build_evidence_manifest.py` — rehash primary evidence and regenerate the audit manifest.
5. `python scripts/analysis/build_profile_summary.py` — parse the separately labelled `.015`/`.016` diagnostics, if those new results are present.
6. `pwsh -NoProfile -File scripts/analysis/run_final_verification.ps1` — check the complete core submission and save `logs/final_core_verification.log`.

Each builder supports `--check` to compare generated files without modifying them. `verify_document_tables.py` additionally checks that the human-readable workload, official, and repeat tables have not drifted from their CSV sources. `run_diagnostic_profiles.sh` is a **separate, optional research experiment** for `.015`/`.016`; do not run it during normal regeneration, and never treat its single-workload results as a compliant Base score. It refuses to overwrite existing IDs.
