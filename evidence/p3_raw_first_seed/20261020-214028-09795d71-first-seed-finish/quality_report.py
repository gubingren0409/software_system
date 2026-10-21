"""Summarize actual raw quality evidence after stop; no new resource or target execution."""
import json
import sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
auth=json.loads((OUT/'continuation/authorization.json').read_bytes())
plan=json.loads(Path(auth['plan_file']).read_bytes())
sys.path.insert(0,plan['windows_archive_directory'])
from autotuner.core import sha256_file
from scripts.p3_clock_contract import atomic_write_json,load
from scripts.raw_clock_contract import audit_clock

session=Path(plan['session_directory'])
admission_roots=[OUT/'continuation',Path(auth['previous_authorization_file']).parent]
snapshots=[]
resource_paths=sorted(list(session.rglob('sample_*.stdout.txt'))+[p for root in admission_roots for p in (root/'admission_resources').glob('sample_*.stdout.txt')])
for path in resource_paths:
    value=load(path)
    if value.get('schema')!='resource-snapshot-v4':
        # The version is recorded, not guessed; accept only actual resource outputs here.
        if 'host_samples' not in value or 'wsl_available_bytes' not in value:
            raise ValueError('Not a resource snapshot: '+str(path))
    snapshots.append(dict(file=str(path),sha256=sha256_file(path),
        purpose=value['purpose'],decision=value['decision'],warnings=value['warnings'],
        rejection_reasons=value['rejection_reasons'],host_available_min_bytes=value['host_minimum_available_bytes'],
        host_commit_min_bytes=value['host_minimum_commit_headroom_bytes'],
        wsl_available_bytes=value['wsl_available_bytes'],
        wsl_swap_used_bytes=value['wsl_swap_total_bytes']-value['wsl_swap_free_bytes'],
        host_cpu_average_percent=value['host_cpu_average_percent'],
        host_cpu_maximum_percent=value['host_cpu_maximum_percent']))
clocks=[]
clock_paths=sorted(list(session.rglob('native_process.json'))+[p for root in admission_roots for p in (root/'admission').glob('native_process.json')])
for path in clock_paths:
    manifest=load(path.parent/'manifest.json')
    audit=audit_clock(path.parent,manifest['context'])
    clocks.append(dict(directory=str(path.parent),
        purpose=manifest['purpose'],intervals=audit['interval_count'],
        responses=audit['response_count'],evidence_integrity_pass=audit['evidence_integrity_pass'],
        raw_reference_pass=audit['raw_reference_pass'],raw_failure_indices=audit['raw_failure_indices'],
        monotonic_warning_indices=audit['monotonic_warning_indices'],errors=audit['errors']))
volume_paths=list(session.rglob('evidence_volume*.json'))+[p for root in admission_roots for p in root.glob('evidence_volume*.json')]
volumes=[dict(file=str(path),**load(path)) for path in volume_paths]
result=dict(schema='first-seed-quality-summary-v1',scope='Post-stop evidence summary, not a recovery certificate or new observation',
    source_sha256=sha256_file(Path(__file__)),resource_snapshots=snapshots,
    resource_snapshot_count=len(snapshots),resource_warning_count=sum(bool(v['warnings']) for v in snapshots),
    minimum_host_available_bytes=min(v['host_available_min_bytes'] for v in snapshots),
    minimum_commit_headroom_bytes=min(v['host_commit_min_bytes'] for v in snapshots),
    minimum_wsl_available_bytes=min(v['wsl_available_bytes'] for v in snapshots),
    maximum_recorded_wsl_swap_used_bytes=max(v['wsl_swap_used_bytes'] for v in snapshots),
    clocks=clocks,native_intervals=sum(v['intervals'] for v in clocks),native_responses=sum(v['responses'] for v in clocks),
    clock_all_pass=all(v['evidence_integrity_pass'] and v['raw_reference_pass'] and not v['errors'] for v in clocks),
    monotonic_warning_intervals=sum(len(v['monotonic_warning_indices']) for v in clocks),
    evidence_volume_checks=len(volumes),evidence_volume_results=volumes)
atomic_write_json(OUT/'quality_report.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('resource_snapshots','clocks','evidence_volume_results')}))
