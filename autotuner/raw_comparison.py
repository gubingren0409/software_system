"""Independent RAW comparison state machine; historical campaign remains Grid-only.

No Grid or validation result is an input to the search state machine. Windows owns
admission, power-event checks and QPC budget; this WSL half owns fresh evaluation.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .core import Config, ConfigSpace, Evaluator, TargetAdapter, sha256_file, sha256_json, utc_now
from .measurement import ConfigurationEvaluator
from .search import RandomSearch, RestartGreedySearch
from .session import restore_complete_group, source_identity
from .timing import relocate_target, require_formal_activation
from scripts.p3_clock_contract import atomic_write_json, load
from scripts.raw_clock_contract import local_path, audit_gate, audit_clock

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'raw-comparison-session-v1'


def comparison_protocol(root=ROOT):
    value = load(root / 'configs/raw_comparison_protocol.json')
    measurement = load(root / 'configs/measurement_protocol.json')
    timing = require_formal_activation(measurement, root)
    if value['schema'] != 'raw-comparison-campaign-v1' or \
            value['measurement_protocol_hash'] != sha256_json(measurement) or \
            value['timing_protocol_hash'] != sha256_json(timing) or \
            value['resource_policy_hash'] != measurement['resource_gate']['policy_hash'] or \
            value['search_protocol_hash'] != sha256_json(load(root / 'configs/search_protocol.json')) or \
            value['algorithms'] != ['random', 'greedy'] or value['prefix_budgets'] != [4, 8, 12] or \
            value['unique_evaluations_per_trajectory'] != 12 or value['matrix_input_seed'] != 20261008:
        raise ValueError('Independent RAW comparison protocol or inherited science differs')
    return value


def strategy_for(space, algorithm):
    kinds = {'random': RandomSearch, 'greedy': RestartGreedySearch}
    if algorithm not in kinds:
        raise ValueError('Unknown comparison algorithm')
    return kinds[algorithm](space, 12, 20261008)


def replay(space, algorithm, observations):
    strategy = strategy_for(space, algorithm)
    for group in observations:
        config = strategy.ask()
        if config is None or asdict(config) != group['config'] or group['classification'] != 'success':
            raise ValueError('Saved own trajectory does not replay; failed groups are not completed observations')
        # Deliberately do not pass group samples, Grid, retests or another algorithm.
        strategy.tell(config, {'classification': group['classification'], 'score_seconds': group['score_seconds']})
    return strategy


def prefixes(space, algorithm, observations):
    strategy = replay(space, algorithm, observations)
    result = []
    for budget in (4, 8, 12):
        if len(observations) < budget:
            continue
        best = min(observations[:budget], key=lambda g: (g['score_seconds'], space.all().index(Config(**g['config']))))
        result.append({'algorithm': algorithm, 'budget': budget, 'best_config': best['config'],
            'median_seconds': best['score_seconds'],
            'terminal_evaluation_raw_seconds': sum(g['evaluation_wall_seconds'] for g in observations[:budget]),
            'cost_scope': 'Completed configuration evaluations only; excludes gates, admission, abandoned attempts and retests'})
    return result


def next_job(state, space, protocol):
    if state['active'] is not None or state['status'] in ('stopped', 'complete'):
        return None
    if state['mode'] == 'validation':
        index = len(state['validation_groups'])
        return {'kind': 'validation', 'config': protocol['validation_order'][index]} if index < 3 else None
    for algorithm in protocol['algorithms']:
        own = state['trajectories'][algorithm]
        strategy = replay(space, algorithm, own['observations'])
        if (config := strategy.ask()) is not None:
            return {'kind': 'search', 'algorithm': algorithm, 'config': asdict(config)}
        candidates = [row['best_config'] for row in prefixes(space, algorithm, own['observations'])]
        for config in candidates:
            if config not in [group['config'] for group in own['retests']]:
                return {'kind': 'retest', 'algorithm': algorithm, 'config': config}
    return None


def commit_observation(state, job, group, space, protocol):
    if state['active']['job'] != job or group['config'] != job['config'] or group['classification'] != 'success':
        raise ValueError('Unexpected or failed group')
    if job['kind'] == 'validation':
        state['validation_groups'].append(group)
    else:
        own = state['trajectories'][job['algorithm']]
        own['observations' if job['kind'] == 'search' else 'retests'].append(group)
        replay(space, job['algorithm'], own['observations'])
        own['prefixes'] = prefixes(space, job['algorithm'], own['observations'])
        own['prefix_retest_mapping'] = [dict(row, retest_attempt=next((g['attempt_id'] for g in own['retests']
            if g['config'] == row['best_config']), None)) for row in own['prefixes']]
    state.update(active=None, status='ready')
    if next_job(state, space, protocol) is None:
        state['status'] = 'complete'


def runtime(plan):
    protocol = comparison_protocol()
    if str(ROOT) != plan['archive_directory'] or sha256_json(protocol) != plan['comparison_protocol_hash']:
        raise ValueError('Comparison archive/protocol identity differs')
    identity = load(local_path(plan['git_identity']))
    if identity['content_sha'] != plan['content_commit']:
        raise ValueError('Comparison content identity differs')
    files = source_identity(ROOT, identity['files'])
    if files != plan['linux_source_identity']:
        raise ValueError('Execution byte identity differs')
    inherited = Path(plan['measurement_archive_directory'])
    for name, expected in plan['inherited_measurement_files'].items():
        if sha256_file(inherited / name) != expected or sha256_file(ROOT / name) != expected:
            raise ValueError('Inherited measurement bytes changed: ' + name)
    measurement = load(ROOT / 'configs/measurement_protocol.json')
    output = local_path(plan['session_directory'])
    data = relocate_target(load(inherited / 'configs/target.json'), inherited / 'configs')
    data['cache_root'] = plan['cache_directory']
    path = output / 'effective_target.json'
    if path.exists() and load(path) != data:
        raise ValueError('Effective target changed')
    if not path.exists():
        atomic_write_json(path, data)
    target = TargetAdapter.load(path, evidence_root=output)
    if sha256_file(target.compiler) != plan['compiler_sha256']:
        raise ValueError('Compiler identity differs')
    fingerprint = {'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
        'comparison_protocol_hash': plan['comparison_protocol_hash'], 'files': files,
        'measurement_content': protocol['inherited_measurement_content'],
        'measurement_protocol_hash': sha256_json(measurement), 'target_hash': sha256_json(data),
        'compiler_sha256': plan['compiler_sha256'], 'compiler_version': target._compiler_version}
    return output, protocol, measurement, target, fingerprint


def initialize(plan):
    output, protocol, measurement, target, fingerprint = runtime(plan)
    if (output / 'checkpoint.json').exists():
        raise ValueError('Never replace a session or reset its budget')
    if plan['mode'] not in ('validation', 'search'):
        raise ValueError('Unknown session mode')
    state = {'schema': VERSION, 'session_id': plan['session_id'], 'fingerprint': fingerprint,
        'mode': plan['mode'], 'status': 'initialized', 'active': None, 'validation_groups': [],
        'trajectories': {name: {'observations': [], 'retests': [], 'prefixes': [], 'prefix_retest_mapping': []}
                         for name in protocol['algorithms']},
        'target_executions': 0, 'reference_generation_calls': 0, 'created_at': utc_now()}
    atomic_write_json(output / 'checkpoint.json', state)
    atomic_write_json(output / 'initial_checkpoint.json', state)
    atomic_write_json(output / 'session.json', {'fingerprint': fingerprint, 'initial_target_executions': 0})
    return 0


def opened(plan, certificate=True):
    output, protocol, measurement, target, fingerprint = runtime(plan)
    state = load(output / 'checkpoint.json')
    if state['schema'] != VERSION or state['fingerprint'] != fingerprint or state['mode'] != plan['mode']:
        raise ValueError('Session/source/protocol identity mismatch')
    if certificate:
        from scripts.raw_comparison_contract import require_certificate
        require_certificate(plan)
    return output, protocol, measurement, target, state


def setup(plan):
    output, protocol, measurement, target, state = opened(plan)
    if not audit_gate(output / 'setup_resources', measurement, 'Formal', {
            'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
            'comparison_protocol_hash': plan['comparison_protocol_hash'], 'purpose': 'setup'}):
        raise ValueError('Matching setup Formal gate required')
    # These immutable, explicitly supplied cache files must be valid BEFORE any
    # TargetAdapter method can fall back to a build/reference generation.
    for name, expected in plan['verified_cache_files'].items():
        if sha256_file(Path(name)) != expected:
            raise ValueError('Verified cache changed; no silent regeneration: ' + name)
    started = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    binaries = {}
    for optimization in ('O0', 'O1', 'O2', 'O3'):
        artifact = target.build_candidate(4096, optimization)
        if artifact.binary_sha256 != plan['expected_artifacts']['binary_hashes'][optimization]:
            raise ValueError('Candidate differs from inherited measurement')
        binaries[optimization] = artifact.binary_sha256
        atomic_write_json(output / 'manifests' / ('candidate_' + optimization + '.json'), load(artifact.binary.parent / 'manifest.json'))
    reference = target.get_reference(4096, 20261008, 'random', 600)
    if reference.reference_key != plan['expected_artifacts']['reference_key'] or reference.data_sha256 != plan['expected_artifacts']['reference_sha256']:
        raise ValueError('Reference differs from inherited measurement')
    generator = target.build_reference_generator(4096)
    atomic_write_json(output / 'manifests/reference_build.json', load(generator.binary.parent / 'manifest.json'))
    atomic_write_json(output / 'manifests/reference.json', reference.metadata)
    for name, expected in plan['verified_cache_files'].items():
        if sha256_file(Path(name)) != expected:
            raise ValueError('Cache unexpectedly changed')
    state.update(status='ready', artifacts=plan['expected_artifacts'], setup_raw_seconds=
                 (time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW) - started) / 1e9)
    atomic_write_json(output / 'checkpoint.json', state)
    return 0


def job_context(plan, job, attempt):
    return {'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
        'comparison_protocol_hash': plan['comparison_protocol_hash'], 'job': job, 'attempt_id': attempt}


def measure(plan, attempt, checks):
    output, protocol, measurement, target, state = opened(plan)
    space = ConfigSpace.load(ROOT / 'configs/config_space.json')
    job = next_job(state, space, protocol)
    if job is None or 'artifacts' not in state:
        raise ValueError('No admissible next group')
    context = job_context(plan, job, attempt)
    if not audit_gate(checks / 'resources', measurement, 'Formal', context) or \
            not audit_clock(checks / 'before', {**context, 'phase': 'before'})['raw_reference_pass']:
        raise ValueError('Matching Formal gate and before clock required')
    stopped = {'value': False}
    signal.signal(signal.SIGTERM, lambda *args: stopped.update(value=True))
    requested = lambda: stopped['value'] or (output / 'PAUSE_REQUEST').exists()
    state.update(status='running', active={'job': job, 'attempt_id': attempt, 'saved_samples': 0})
    atomic_write_json(output / 'checkpoint.json', state)
    def progress(index):
        atomic_write_json(output / 'progress.json', {'job': job, 'attempt_id': attempt, 'sample_index': index,
            'stage': 'warmup' if index == 0 else 'measurement', 'runner_pid': os.getpid(), 'at': utc_now()})
    def sampled(sample):
        state['active']['saved_samples'] = sample['sample_index'] + 1
        state['target_executions'] += bool(sample.get('timed_command'))
        atomic_write_json(output / 'checkpoint.json', state)
        print(json.dumps({'event': 'sample_saved', 'run_id': sample['run_id'], 'sample_index': sample['sample_index'],
              'classification': sample['classification']}), flush=True)
    script = plan['windows_archive_directory'].replace('\\', '/') + '/scripts/check_p2_resources.ps1'
    host = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-File', script,
            '-Mode', 'Snapshot', '-RuntimeRoot', str(ROOT)]
    executor = Evaluator(target, host, requested)
    evaluator = ConfigurationEvaluator(executor, measurement, sha256_json(measurement), output, sampled, progress)
    # Startup, source/cache checks and gates are finished BEFORE the host starts
    # its envelope. The request/response markers expose the exact evaluation scope.
    print(json.dumps({'event': 'READY', 'pid': os.getpid(), 'attempt_id': attempt, 'job': job}), flush=True)
    if sys.stdin.readline() != 'RUN ' + attempt + '\n' or requested():
        raise ValueError('Missing matching RUN handshake or pause request')
    raw_start = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    group = evaluator.evaluate(Config(**job['config']), attempt_id=attempt, purpose=job['kind'])
    raw_end = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    scope = {'schema': 'raw-comparison-evaluation-scope-v1', 'attempt_id': attempt,
        'raw_start_ns': raw_start, 'raw_end_ns': raw_end, 'raw_seconds': (raw_end - raw_start) / 1e9,
        'group_file': str(output / 'configurations' / (job['kind'] + '_' + attempt + '.json')),
        'scope': 'Immediately before through immediately after ConfigurationEvaluator.evaluate'}
    print(json.dumps({'event': 'FINISHED', **scope}), flush=True)
    atomic_write_json(checks / 'evaluation_scope.json', scope)
    state['status'] = 'awaiting_continuity_and_after_check' if group['classification'] == 'success' else 'stopped'
    atomic_write_json(output / 'checkpoint.json', state)
    return 0 if group['classification'] == 'success' else 3


def accept(plan, attempt, checks):
    from scripts.raw_comparison_contract import verify_group
    output, protocol, measurement, target, state = opened(plan)
    if state['active'] is None or state['active']['attempt_id'] != attempt:
        raise ValueError('Active group differs')
    job = state['active']['job']
    path = output / 'configurations' / (job['kind'] + '_' + attempt + '.json')
    group = load(path)
    restore_complete_group(group, measurement)
    verify_group(plan, job, attempt, group, checks)
    group.update(checks_directory=str(checks), measured_group_sha256=sha256_file(path))
    commit_observation(state, job, group, ConfigSpace.load(ROOT / 'configs/config_space.json'), protocol)
    atomic_write_json(output / 'checkpoint.json', state)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('mode', choices=('init', 'setup', 'measure', 'accept', 'status'))
    parser.add_argument('--attempt-id'); parser.add_argument('--checks-directory')
    args = parser.parse_args(); plan = load(args.plan)
    if args.mode == 'init': return initialize(plan)
    if args.mode == 'setup': return setup(plan)
    if args.mode == 'status':
        print(json.dumps(opened(plan, False)[-1])); return 0
    function = measure if args.mode == 'measure' else accept
    return function(plan, args.attempt_id, local_path(args.checks_directory))


if __name__ == '__main__':
    raise SystemExit(main())
