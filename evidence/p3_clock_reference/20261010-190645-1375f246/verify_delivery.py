"""Final saved-evidence checks; no new resource, clock or target executions."""
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file
from scripts.p3_clock_contract import atomic_write_json, load
from scripts.p3_clock_reference import audit_diagnostic

review = audit_diagnostic(HERE)
assert review == load(HERE / 'independent_diagnostic.json')
assert review['evidence_integrity_pass'] and review['diagnostic_complete']
assert not review['diagnostic_certifiable'] and review['interval_count'] == 30
assert [(x['condition'], x['index']) for x in review['checks'] if not x['reference_match_pass']] == [('B', 1), ('B', 2)]
rows = list(csv.DictReader((HERE / 'interval_summary.csv').open()))
for row, checked in zip(rows, review['checks'], strict=True):
    for key, value in checked['guest_durations_ns'].items():
        assert float(row[key.removesuffix('_ns') + '_seconds']) == value / 1e9
summary = load(HERE / 'delivery_summary.json')
assert summary['postprocessing_source_sha256'] == sha256_file(HERE / 'finish.py')
assert load(HERE / 'clean_validation.json')['pass']
assert all(r['matches_before'] for r in load(HERE / 'history_protection_after.json'))
assert all(summary[k] == 0 for k in ('new_recovery_calls', 'formal_target_executions',
    'search_configurations', 'complete_trajectories', 'candidate_retest_groups'))
operations = []
rejected_helper_records = []
failed_wrappers = {'clean_python_version.operation.json', 'clean_targeted_tests.operation.json',
                   'clean_cli_help.operation.json', 'clean_configs.operation.json'}
for file in sorted(HERE.glob('*.operation.json')):
    op = load(file)
    if 'qpc_seconds' not in op: continue  # This check's parent capture is in progress.
    assert type(op['returncode']) is int and not op['timed_out'], file.name
    streams = {stream: {'recorded_sha256': op[stream + '_sha256'],
                        'actual_sha256': sha256_file(HERE / op[stream + '_path'])}
               for stream in ('stdout', 'stderr')}
    if file.name in failed_wrappers:
        # Preserve, explicitly reject, and never repair the original receipts:
        # Windows execv let their child write after the parent capture ended.
        rejected_helper_records.append({'name': file.name, 'streams': streams,
            'status': 'rejected_failed_wrapper_not_used_for_acceptance',
            'recorded_parent_exit_not_reliable_child_exit': op['returncode']})
    else:
        assert all(v['recorded_sha256'] == v['actual_sha256'] for v in streams.values()), file.name
    operations.append({'name': file.name, 'returncode': op['returncode']})
links = 0
for relative in ('README.md', 'report.md', 'docs/P3_CLOCK_REFERENCE.md', 'docs/P3_CLOCK_CONTRACT.md',
                 'docs/P3_FIRST_SEED_STATUS.md', 'docs/WORK_LOG.md', 'docs/AUDIT_HANDOFF.md'):
    path = ROOT / relative
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        target = unquote(target.strip('<>').split('#')[0])
        if not target or re.match(r'^[a-zA-Z]+://', target): continue
        assert (path.parent / target).exists(), (relative, target)
        links += 1
unchanged = subprocess.check_output(['git', 'diff', '--name-only',
    '50cd24e59d6a99304b604560a057a961d06bfb14', '--', 'code/original', 'code/working',
    'autotuner', 'configs', 'evidence/p2', 'evidence/p3', 'evidence/p3_clock_repair',
    'evidence/p3_clock_contract', 'evidence/p3_resource_policy', 'evidence/p3_memory_policy'], cwd=ROOT)
assert not unchanged
result = {'pass': True, 'diagnostic_only': True, 'saved_evidence_recomputed': True,
          'old_files_and_formal_source_unchanged': True, 'verified_relative_links': links,
          'operation_stream_hashes': operations, 'rejected_helper_records': rejected_helper_records,
          'evidence_integrity_scope': 'Diagnostic raw data, frozen identities, protected history, and final v2 clean checks. Four initial failed-wrapper receipts explicitly excluded, not repaired.',
          'extra_samples_or_targets': 0,
          'verifier_sha256': sha256_file(Path(__file__))}
atomic_write_json(HERE / 'delivery_verification.json', result)
print(json.dumps(result, indent=2))
