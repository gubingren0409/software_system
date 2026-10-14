"""Export an exact committed runner, verify it, initialize two EMPTY independent sessions.

No clock collection, matrix target, reference generation or search is performed.
Run from the repository; all subsequent execution uses the exported content.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, sha256_json
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, capture, load, wsl_path

SCIENTIFIC_FILES = ('code/original/matrix_multiplication.c', 'code/working/matrix_multiplication.c',
    'code/working/matrix_input.h', 'code/working/reference_generator.c', 'autotuner/core.py',
    'autotuner/measurement.py', 'autotuner/search.py', 'autotuner/timing.py',
    'configs/target.json', 'configs/config_space.json', 'configs/measurement_protocol.json',
    'configs/raw_formal_timing_protocol.json', 'configs/resource_policy.json', 'configs/search_protocol.json')


def prepare(content, directory):
    if os.name != 'nt': raise ValueError('Prepare from Windows project root')
    directory.mkdir(parents=True, exist_ok=False)
    def operation(argv, name, timeout=120):
        value = capture(argv, directory / 'operations', name, 'raw-comparison-prepare', timeout=timeout)
        if value['returncode'] != 0 or value['timed_out']: raise ValueError(name + ' failed')
        return (directory / 'operations' / value['stdout_path']).read_text(encoding='utf-8')
    actual = operation(['git', 'rev-parse', content], 'resolve_content').strip()
    if content != actual: raise ValueError('Use complete committed content SHA')
    tree = operation(['git', 'ls-tree', '-r', content], 'git_tree')
    files = {}
    for line in tree.splitlines():
        meta, path = line.split('\t', 1)
        if path == '.gitattributes' or (path.split('/')[0] in ('autotuner', 'scripts', 'configs', 'tests', 'code') and
                path.endswith(('.py', '.ps1', '.json', '.c', '.h')) and
                (not path.startswith('code/original/') or path == 'code/original/matrix_multiplication.c')):
            files[path] = meta.split()[2]
    archive = Path(tempfile.gettempdir()) / ('matrix-raw-comparison-' + content)
    archive.mkdir(exist_ok=False)
    tar = archive.parent / ('matrix-raw-comparison-' + content + '.tar')
    operation(['git', 'archive', '--format=tar', '--output=' + str(tar), content, '.gitattributes',
        'autotuner', 'code/working', 'code/diagnostics', 'code/original/matrix_multiplication.c', 'configs', 'scripts', 'tests'], 'git_archive')
    with tarfile.open(tar) as stream: stream.extractall(archive, filter='data')
    linux_archive = '/var/tmp/matrix-raw-comparison-content-' + content
    def linux(args): return ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', '/tmp', '--', *args]
    operation(linux(['mkdir', linux_archive]), 'create_wsl_archive')
    operation(linux(['tar', '-xf', wsl_path(tar), '-C', linux_archive]), 'extract_wsl_archive')
    identity = {'content_sha': content, 'files': files}
    identity_path = directory / 'git_identity.json'; atomic_write_json(identity_path, identity)
    windows_identity = source_identity(archive, files)
    atomic_write_json(directory / 'windows_source_identity.json', windows_identity)
    def execution(args):
        return ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', linux_archive, '--', 'env', '-u', 'PYTHONPATH',
                'PYTHONDONTWRITEBYTECODE=1', *args]
    code = 'from pathlib import Path; import json; from autotuner.session import source_identity; print(json.dumps(source_identity(Path.cwd(),json.load(open(' + repr(wsl_path(identity_path)) + '))["files"])))'
    linux_identity = json.loads(operation(execution(['python3', '-c', code]), 'linux_source_identity'))
    atomic_write_json(directory / 'linux_source_identity.json', linux_identity)
    operation([sys.executable, '-X', 'utf8', str(archive / 'scripts/verify_raw_comparison_code.py')], 'clean_windows_focused_tests')
    operation(execution(['python3', 'scripts/verify_raw_comparison_code.py']), 'clean_wsl_focused_tests')
    operation([sys.executable, '-X', 'utf8', str(archive / 'scripts/start_raw_comparison.py'), '--help'], 'clean_controller_help')
    operation(execution(['python3', '-m', 'autotuner', '--help']), 'clean_cli_help')
    config_output = operation(execution(['python3', '-m', 'autotuner', 'list-configs']), 'clean_list_configs')
    configs = json.loads(config_output)
    if len(configs) != 20 or len({json.dumps(c, sort_keys=True) for c in configs}) != 20:
        raise ValueError('20 unique configuration check failed')
    old = load(ROOT / 'evidence/p3_raw_grid/20261011-021601/final-content/plan.json')
    old_session = Path(old['session_directory']); old_state = load(old_session / 'checkpoint.json')
    inherited = Path('\\\\wsl.localhost\\Ubuntu-24.04' + old['archive_directory'].replace('/', '\\'))
    scientific = {name: sha256_file(inherited / name) for name in SCIENTIFIC_FILES}
    for name, expected in scientific.items():
        if sha256_file(archive / name) != expected:
            raise ValueError('Scientific content changed: ' + name)
    cache_files = {}
    for name in ('candidate_O0', 'candidate_O1', 'candidate_O2', 'candidate_O3', 'reference_build'):
        metadata = load(old_session / 'manifests' / (name + '.json'))
        binary_dir = str(Path(metadata['command'][-1]).parent).replace('\\', '/')
        for filename in ('manifest.json', 'candidate' if name.startswith('candidate_') else 'reference_generator'):
            path = binary_dir + '/' + filename
            windows = Path('\\\\wsl.localhost\\Ubuntu-24.04' + path.replace('/', '\\'))
            if not windows.is_file() and filename == 'reference_generator':
                path = binary_dir + '/reference-generator'; windows = Path('\\\\wsl.localhost\\Ubuntu-24.04' + path.replace('/', '\\'))
            cache_files[path] = sha256_file(windows)
    reference_dir = old['cache_directory'] + '/reference/' + old_state['artifacts']['reference_key']
    for filename in ('manifest.json', 'reference.bin'):
        path = reference_dir + '/' + filename
        cache_files[path] = sha256_file(Path('\\\\wsl.localhost\\Ubuntu-24.04' + path.replace('/', '\\')))
    # Share only verified immutable build/reference files. New performance-cache
    # writes have a separate root and cannot overwrite the closed Grid's cache.
    cache = '/var/tmp/matrix-raw-comparison-cache-' + content
    operation(linux(['mkdir', cache]), 'create_independent_cache')
    for kind in ('build', 'reference'):
        operation(linux(['ln', '-s', old['cache_directory'] + '/' + kind, cache + '/' + kind]), 'link_verified_' + kind)
    compiler = operation(execution(['sha256sum', '/usr/bin/gcc']), 'compiler_sha').split()[0]
    if compiler != old['compiler_sha256']: raise ValueError('Compiler differs; stop rather than silently change experiment')
    operation(execution(['/usr/bin/gcc', '--version']), 'compiler_version')
    operation(execution(['python3', '--version']), 'python_version')
    allowed = json.loads(operation(execution(['python3', '-c', 'import os,json; print(json.dumps(sorted(os.sched_getaffinity(0))))']), 'allowed_cpus'))
    probe = '/var/tmp/matrix-raw-comparison-probe-' + content
    operation(linux(['mkdir', probe]), 'create_probe_directory')
    source = linux_archive + '/code/diagnostics/clock_fixed_work_probe.c'; binary = probe + '/probe'
    compile_command = ['/usr/bin/gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', source, '-o', binary]
    operation(execution(compile_command), 'compile_probe')
    binary_hash = operation(execution(['sha256sum', binary]), 'probe_binary_hash').split()[0]
    build = {'content_commit': content, 'source_path': source, 'source_sha256': linux_identity['code/diagnostics/clock_fixed_work_probe.c']['executed_sha256'],
             'compiler_sha256': compiler, 'compile_command': compile_command, 'binary': binary, 'binary_sha256': binary_hash}
    build_path = directory / 'probe_build.json'; atomic_write_json(build_path, build)
    comparison = load(archive / 'configs/raw_comparison_protocol.json')
    plans = {}
    for mode in ('validation', 'search'):
        session = uuid.uuid4().hex; output = directory / (mode + '-' + session[:8])
        path = directory / (mode + '_plan.json')
        plan = {'schema': 'raw-comparison-plan-v1', 'mode': mode, 'content_commit': content,
            'session_id': session, 'plan_file': str(path), 'windows_archive_directory': str(archive),
            'archive_directory': linux_archive, 'session_directory': str(output),
            'recovery_directory': str(output / 'admission'), 'git_identity': str(identity_path),
            'git_identity_sha256': sha256_file(identity_path), 'windows_source_identity': windows_identity,
            'linux_source_identity': linux_identity, 'source_archive_tar_sha256': sha256_file(tar),
            'measurement_content': old['content_commit'], 'measurement_archive_directory': old['archive_directory'],
            'inherited_measurement_files': scientific, 'verified_cache_files': cache_files,
            'expected_artifacts': old_state['artifacts'], 'cache_directory': cache,
            'compiler_sha256': compiler, 'allowed_cpus': allowed, 'probe_build_manifest': str(build_path),
            'comparison_protocol_hash': sha256_json(comparison), 'measurement_protocol_hash': old['measurement_protocol_hash'],
            'timing_protocol_hash': old['timing_protocol_hash']}
        atomic_write_json(path, plan)
        operation(execution(['python3', '-m', 'autotuner.raw_comparison', '--plan', wsl_path(path), 'init']), 'initialize_' + mode)
        plans[mode] = str(path)
    atomic_write_json(directory / 'prepare_summary.json', {'content_commit': content, 'plans': plans,
        'focused_tests_windows': 19, 'focused_tests_wsl': 19, 'real_matrix_targets': 0,
        'native_clock_intervals': 0, 'reference_generation_calls': 0, 'unique_configurations': 20,
        'scientific_files_byte_identical': True})
    print(json.dumps(plans))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content-sha', required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); prepare(args.content_sha, args.output.resolve())
