"""Read-only postprocessing and clean-code checks; never launch clock/target samples."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, sha256_json, utc_now
from scripts.p3_clock_contract import capture, atomic_write_json, load, snapshot_campaign, wsl_path
from scripts.p3_clock_reference import audit_diagnostic


def run(name, command, timeout=90, expected=0):
    record = capture(command, HERE, name, HERE.name, timeout=timeout)
    print(json.dumps({'operation': name, 'returncode': record['returncode'],
                      'qpc_seconds': record['qpc_seconds']}), flush=True)
    assert record['returncode'] == expected, name
    return record


manifest = load(HERE / 'manifest.json')
source = manifest['source_commit']
clean = ROOT / 'build' / ('clock-reference-clean-' + source[:8])

if sys.argv[1] == 'clean':
    # Export only dependencies for these relevant checks, not historical large data.
    assert not clean.exists(), 'Use an independent empty destination'
    clean.mkdir(parents=True)
    archive = clean.with_suffix('.tar')
    paths = ['autotuner', 'configs', 'code/original', 'code/working', 'code/diagnostics',
             'scripts/p3_clock_contract.py', 'scripts/p3_clock_reference.py',
             'scripts/run_clock_reference.py', 'scripts/collect_clock_reference_environment.py',
             'tests/test_clock_reference.py']
    old = 'evidence/p3_memory_policy/20261010-174802-11f7775c/recovery/'
    paths.extend(old + name + '.wsl.json' for name in ('window_A', 'window_B'))
    with archive.open('wb') as stream:
        subprocess.run(['git', 'archive', '--format=tar', source, '--', *paths],
                       cwd=ROOT, stdout=stream, check=True)
    with tarfile.open(archive) as stream:
        stream.extractall(clean, filter='data')
    identity = []
    for relative, digest in manifest['source_sha256'].items():
        raw = (ROOT / relative).read_bytes()
        exported = (clean / relative).read_bytes()
        git_bytes = subprocess.check_output(['git', 'show', source + ':' + relative], cwd=ROOT)
        assert raw == exported == git_bytes, relative
        assert hashlib.sha256(raw).hexdigest() == digest, relative
        identity.append({'path': relative, 'runtime_sha256': digest,
                         'git_blob_sha1': subprocess.check_output(['git', 'rev-parse', source + ':' + relative],
                                                                  cwd=ROOT, text=True).strip(),
                         'git_bytes_sha256': hashlib.sha256(git_bytes).hexdigest(),
                         'clean_bytes_sha256': hashlib.sha256(exported).hexdigest(),
                         'byte_identical': True, 'crlf_count': raw.count(b'\r\n'),
                         'lf_count': raw.count(b'\n')})
    teacher = 'code/original/matrix_multiplication.c'
    assert sha256_file(clean / teacher) == sha256_file(ROOT / teacher) == \
        '188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15'
    atomic_write_json(HERE / 'clean_export.json', {
        'source_commit': source, 'command': ['git', 'archive', '--format=tar', source, '--', *paths],
        'archive_sha256': sha256_file(archive), 'directory': str(clean), 'files': identity,
        'teacher_byte_identity_pass': True, 'initial_git_directory_present': (clean / '.git').exists(),
        'initial_pycache_count': len(list(clean.rglob('__pycache__'))),
        'purpose': 'Relevant auxiliary code checks only; not a recovery or matrix measurement'})
    print('Export complete. Use clean_continue for logged checks with real child exits.', flush=True)
elif sys.argv[1] == 'clean_continue':
    # Preserve the failed Windows-only list-configs receipt and export. The
    # target compiler is Linux GCC, so run that command in the clean WSL path.
    wrapper = ('import os,sys,subprocess; os.chdir(sys.argv[1]); os.environ.pop("PYTHONPATH",None); '
               'sys.exit(subprocess.run([sys.executable,"-B","-X","utf8",*sys.argv[2:]]).returncode)')
    prefix = [sys.executable, '-B', '-X', 'utf8', '-c', wrapper, str(clean)]
    run('clean_returncode_negative_control', prefix + ['-c', 'raise SystemExit(7)'], expected=7)
    run('clean_python_version_v2', prefix + ['--version'])
    run('clean_targeted_tests_v2', prefix + ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_clock_reference.py', '-v'])
    run('clean_cli_help_v2', prefix + ['-m', 'autotuner', '--help'])
    linux_prefix = ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', wsl_path(clean), '--',
                    'env', '-u', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE=1', 'timeout', '45']
    run('clean_configs_wsl', linux_prefix + ['python3', '-B', '-m', 'autotuner', 'list-configs'])
    configs = json.loads((HERE / 'clean_configs_wsl.stdout.txt').read_text())
    assert len(configs) == 20 and len({(x['optimization'], x['block_size']) for x in configs}) == 20
    binary = wsl_path(clean / 'clock_reference_probe')
    run('clean_compile', linux_prefix + ['/usr/bin/gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
        wsl_path(clean / 'code/diagnostics/clock_reference_probe.c'), '-o', binary])
    run('clean_binary_identity', linux_prefix + ['sha256sum', binary])
    assert (HERE / 'clean_binary_identity.stdout.txt').read_text().split()[0] == manifest['binary_sha256']
    atomic_write_json(HERE / 'clean_validation.json', {'pass': True, 'source_commit': source,
        'targeted_tests': 11, 'unique_configs': 20, 'compiled_binary_matches_executed_binary': True,
        'windows_wrapper_negative_control_exit': 7, 'extra_clock_intervals': 0, 'matrix_target_executions': 0,
        'first_failure_retained': 'clean_entry/clean_configs: Linux compiler unavailable on native Windows; execv wrapper did not propagate actual exit. v2 wrapper checked with negative control.',
        'helper_source_sha256': sha256_file(Path(__file__))})
elif sys.argv[1] == 'protect':
    from autotuner.session import source_identity
    plan = load(ROOT / 'evidence/p3_memory_policy/20261010-174802-11f7775c/session_plan.json')
    preflight = load(HERE / 'd6811cad_before.json')['checkpoint']['preflight_identity']
    identity = load(plan['git_identity'])
    assert identity['content_sha'] == plan['content_commit'] == manifest['retained_formal_content']
    worktree = source_identity(ROOT, identity['files'])
    assert all(worktree[path]['git_content_sha256'] == item['git_content_sha256']
               for path, item in preflight['files'].items())
    expected = {plan['archive_directory'] + '/' + path: item['executed_sha256']
                for path, item in preflight['files'].items()}
    run('retained_archive_hashes', ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', '/tmp', '--',
                                   'timeout', '45', 'sha256sum', *expected], 70)
    actual = {line.split(maxsplit=1)[1]: line.split()[0]
              for line in (HERE / 'retained_archive_hashes.stdout.txt').read_text().splitlines()}
    assert actual == expected
    frozen = {}
    for path in ('configs/resource_policy.json', 'configs/measurement_protocol.json',
                 'configs/p3_campaign_protocol.json', 'configs/timing_audit_protocol.json'):
        current = (ROOT / path).read_bytes()
        old = subprocess.check_output(['git', 'show', manifest['retained_formal_content'] + ':' + path], cwd=ROOT)
        assert current == old, path
        frozen[path] = {'raw_sha256': sha256_file(ROOT / path), 'canonical_sha256': sha256_json(load(ROOT / path)),
                        'byte_identical_to_retained_formal_content': True}
    atomic_write_json(HERE / 'retained_identity.json', {
        'pass': True, 'formal_content': plan['content_commit'], 'session_id': plan['session_id'],
        'archive': plan['archive_directory'], 'archive_file_count': len(expected),
        'archive_actual_sha256': actual, 'worktree_identity': worktree,
        'frozen_protocols': frozen, 'byte_identity_distinct_from_git_normalization': True})
    protection = []
    for before in load(HERE / 'history_protection_before.json'):
        prefix = before['prefix']
        paths = subprocess.check_output(['git', 'ls-files', '--', prefix], cwd=ROOT, text=True).splitlines()
        after = {'prefix': prefix, 'count': len(paths),
                 'raw_map_sha256': sha256_json({p: sha256_file(ROOT / p) for p in paths})}
        protection.append({**after, 'matches_before': after == before})
    assert all(item['matches_before'] for item in protection)
    for name, path in (
        ('d6811cad', ROOT / 'evidence/p3_memory_policy/20261010-174802-11f7775c/campaign-d6811cad'),
        ('7405fcc3', ROOT / 'evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3'),
        ('e308bfb', ROOT / 'evidence/p3/campaign-e308bfb')):
        before = load(HERE / (name + '_before.json'))
        after = snapshot_campaign(path)
        assert all(before[key] == after[key] for key in before if key not in ('captured_at', 'captured_qpc'))
        atomic_write_json(HERE / (name + '_after.json'), after)
    atomic_write_json(HERE / 'history_protection_after.json', protection)
    code = '''import json,pathlib
found=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit(): continue
 try:
  args=[a.decode(errors='replace') for a in (p/'cmdline').read_bytes().split(bytes([0])) if a]
  if ('autotuner' in args and 'campaign' in args) or any(a.startswith('/var/tmp/matrix-clock-reference-20261010-190645-1375f246/clock_reference_probe') or a.startswith('/var/tmp/matrix-autotuner-p3-10245102457/cache/') for a in args): found.append({'pid':int(p.name),'command':args})
 except OSError: pass
print(json.dumps({'matching_experiment_processes':found,'no_process_terminated':True}))
'''
    run('process_inventory', ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', '/tmp', '--', 'timeout', '20', 'python3', '-c', code], 45)
    assert not load(HERE / 'process_inventory.stdout.txt')['matching_experiment_processes']
    run('git_tool_version', ['git', '--version'])
    run('wsl_tool_version', ['wsl.exe', '--version'])
elif sys.argv[1] == 'summarize':
    review = audit_diagnostic(HERE)
    assert review == load(HERE / 'independent_diagnostic.json')
    assert review['evidence_integrity_pass'] and review['diagnostic_complete'] and not review['diagnostic_certifiable']
    rows = [json.loads(line) for line in (HERE / 'intervals.jsonl').read_text().splitlines()]
    table = []
    for row, checked in zip(rows, review['checks']):
        s, e = row['start']['response'], row['end']['response']
        table.append({'condition': row['condition'], 'index_zero_based': row['index'],
            **{k: checked[k] for k in ('host_lower_seconds', 'host_upper_seconds', 'uncertainty_seconds',
                'allowance_seconds', 'reference_match_pass', 'raw_within_host', 'realtime_within_host', 'boottime_within_host')},
            **{k.removesuffix('_ns') + '_seconds': v / 1e9 for k, v in checked['guest_durations_ns'].items()},
            'start_cpu_before': s['cpu_before'], 'start_cpu_after': s['cpu_after'],
            'end_cpu_before': e['cpu_before'], 'end_cpu_after': e['cpu_after'],
            'start_read_span_ns': checked['read_spans_ns'][0], 'end_read_span_ns': checked['read_spans_ns'][1]})
    with (HERE / 'interval_summary.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=table[0]); writer.writeheader(); writer.writerows(table)
    costs = []
    for file in sorted(HERE.glob('*.operation.json')):
        op = load(file)
        if 'qpc_seconds' not in op:
            continue  # The enclosing summarize capture is still running.
        name = file.name.removesuffix('.operation.json')
        nested = ('diagnostic_entry' if name == 'wsl_environment' else
                  'clean_entry' if name in ('clean_python_version', 'clean_targeted_tests', 'clean_cli_help', 'clean_configs') else
                  'clean_entry_v2' if name.startswith('clean_') and name not in ('clean_entry', 'clean_entry_v2') else
                  'protection_entry' if name in ('retained_archive_hashes', 'process_inventory', 'git_tool_version', 'wsl_tool_version') else None)
        costs.append({'operation': file.stem, 'command': op['command'], 'returncode': op['returncode'],
                      'qpc_seconds': op['qpc_seconds'],
                      'nested_in': nested})
    atomic_write_json(HERE / 'costs.json', {'operations': costs,
        'diagnostic_entry_qpc_seconds': load(HERE / 'diagnostic_entry.operation.json')['qpc_seconds'],
        'native_probe_qpc_seconds': review['native_elapsed_qpc_seconds'],
        'collection_qpc_seconds': (load(HERE / 'native_process.json')['qpc_end'] -
                                  load(HERE / 'native_process.json')['collection_start_qpc']) /
                                  load(HERE / 'native_process.json')['qpc_frequency'],
        'formal_execution_increment_seconds': 0, 'candidate_retest_increment_seconds': 0,
        'formal_gate_wait_increment_seconds': 0, 'abandoned_attempt_increment_seconds': 0,
        'non_nested_captured_operations_seconds': sum(x['qpc_seconds'] for x in costs if x['nested_in'] is None),
        'scope': 'QPC operation durations only. Native/metadata and clean/protect subcommands are nested; do not add them again. Enclosing summarize capture, editing/model time and push excluded; not an end-to-end task total.'})
    atomic_write_json(HERE / 'delivery_summary.json', {'status': 'P3_CLOCK_BLOCKED', 'captured_at': utc_now(),
        'diagnostic_source_commit': source, 'postprocessing_source_sha256': sha256_file(Path(__file__)),
        'manifest_sha256': sha256_file(HERE / 'manifest.json'),
        'diagnostic_binary_sha256': manifest['binary_sha256'],
        'formal_content_commit': manifest['retained_formal_content'], 'session_id': manifest['retained_session'],
        'evidence_integrity_pass': True, 'reference_match_pass': False, 'execution_complete': False,
        'timing_checks_pass': False, 'comparison_ready': False,
        'diagnostic_interval_count': len(rows), 'default_interval_count': 20,
        'default_failures_zero_based': [{'condition': r['condition'], 'index': r['index']} for r in review['checks'][:20] if not r['reference_match_pass']],
        'groups': {name: {'count': sum(r['condition'] == name for r in review['checks']),
                          'monotonic_host_passes': sum(r['condition'] == name and r['reference_match_pass'] for r in review['checks'])} for name in 'ABCD'},
        'raw_host_passes': len(rows) - review['all_raw_host_mismatch_count'],
        'indeterminate_count': review['indeterminate_count'],
        'maximum_boundary_uncertainty_seconds': max(r['uncertainty_seconds'] for r in review['checks']),
        'maximum_read_span_ns': max(max(r['read_spans_ns']) for r in review['checks']),
        'new_recovery_calls': 0, 'new_recovery_intervals': 0, 'formal_gate_status': 'not_performed',
        'formal_target_executions': 0, 'search_configurations': 0, 'complete_trajectories': 0,
        'prefix_results': 0, 'candidate_retest_groups': 0, 'partial_groups': 0, 'abandoned_groups': 0,
        'historical_e308bfb': {'complete_search_configurations': 3, 'raw_target_records': 23,
            'complete_group_records': 18, 'abandoned_records': 3, 'pending_restart_records': 2},
        'resource_policy_modified': False, 'clock_admission_modified': False, 'formal_source_modified': False,
        'history_protection_pass': all(r['matches_before'] for r in load(HERE / 'history_protection_after.json')),
        'experiment_processes_remaining': 0,
        'decision': 'Predeclared branch 3: default libc MONOTONIC mismatch in busy B; do not certify, do not recover/resume. C/D idle passes cannot isolate path vs migration or replace default busy failures.',
        'cause': 'unknown; diagnostic consistency is not absolute physical accuracy; no calibration or filtering'})
    print(json.dumps(load(HERE / 'delivery_summary.json'), indent=2))
else:
    raise ValueError('Unknown phase')
