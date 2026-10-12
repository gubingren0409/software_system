"""Read-only final delivery checks; no resource gates, probes or target executions."""
import hashlib, importlib, importlib.util, json, os, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def bootstrap():
    freeze = json.loads((HERE/'auxiliary_freeze.json').read_bytes())
    spec = importlib.util.spec_from_file_location('frozen_helper', Path(freeze['archive_directory'])/'scripts/raw_grid_segment.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    auth = helper.read(HERE/'window/authorization.json'); plan = helper.read(auth['plan_file'])
    return helper, auth, plan, helper.frozen(plan)


def costs(helper, f):
    checked = []; pending = []
    closed = importlib.import_module('scripts.raw_clock_contract').checked_operation
    for path in HERE.rglob('*.operation.json'):
        data = helper.read(path)
        if data.get('pid') == os.getpid() and 'qpc_end' not in data:
            pending.append(str(path.relative_to(HERE))); continue
        closed(path.parent, path.name.removesuffix('.operation.json'))
        checked.append({'path':path.relative_to(HERE).as_posix(), **{k:data[k] for k in ('qpc_start','qpc_end','qpc_frequency','qpc_seconds','returncode')}})
    # All intervals in THIS root share the recorded current Windows boot, not
    # merely a frequency. Never use this relation for first/previous windows.
    pre = helper.read(HERE/'window/operations/windows_environment.stdout.txt')
    post = helper.read(HERE/'operations/post_windows.stdout.txt')
    if pre['windows_boot_utc'][:23] != post['boot'][:23]: raise ValueError('Current auxiliary interval epoch cannot be established')
    wrappers = [o for o in checked if o['path'].startswith('operations/')]
    current = helper.read(HERE/'window/window.json')
    manual = {'path':'manual_budget_envelope','qpc_start':current['qpc_start'],'qpc_end':current['qpc_end'],
        'qpc_frequency':current['qpc_frequency'],'qpc_seconds':current['window_qpc_seconds']}
    candidates = []; nested = []; overlap = []
    for o in wrappers:
        if o['path']=='operations/manual_run.operation.json':
            nested.append({'path':o['path'],'inside':'outer wrapper (includes manual budget envelope); excluded, not extra total'}); continue
        parents = [p for p in wrappers+[manual] if p['path']!=o['path'] and p['qpc_frequency']==o['qpc_frequency']
            and p['qpc_start'] <= o['qpc_start'] <= o['qpc_end'] <= p['qpc_end']]
        if parents:
            nested.append({'path':o['path'],'inside':[p['path'] for p in parents]}); continue
        candidates.append(o)
    candidates.sort(key=lambda o:o['qpc_start'])
    for a,b in zip(candidates,candidates[1:]):
        if a['qpc_frequency']!=b['qpc_frequency'] or a['qpc_end']>b['qpc_start']: overlap.append([a['path'],b['path']])
    if overlap: raise ValueError('Auxiliary outer envelopes overlap')
    value = {'non_overlapping_closed_auxiliary_qpc_seconds':sum(o['qpc_seconds'] for o in candidates),
        'included':candidates,'excluded_nested':nested,'all_closed_operation_count':len(checked),'closed_operations':checked,
        'own_parent_pending_at_snapshot':pending,'current_boot_epoch':pre['windows_boot_utc'],
        'first_previous_manual_budget_sum_seconds':current['cumulative_active_qpc_seconds'],
        'scope':'Auxiliary envelopes are deduplicated within current recorded Windows boot only. All window/operations, admission, resource and clock captures are nested in manual envelope. Exclude outer manual launch, in-window power query, nested post snapshots. No cross-epoch absolute subtraction, no addition to nested RAW costs. Edits/model time/push are not captured: not a whole-turn total. Manual QPC includes standby, no refund.'}
    f.atomic_write_json(HERE/'final_cost_index.json', value)
    return value


def main():
    helper, auth, plan, f = bootstrap(); errors = []
    helper.verify_protection(auth, plan)
    state = helper.read(Path(plan['session_directory'])/'checkpoint.json')
    if len(state['completed'])!=20 or state['target_executions']!=120 or state['active'] is not None or state['abandoned_attempts']:
        errors.append('Final session not complete')
    index = costs(helper,f)
    revision = helper.read(HERE/'postprocess_revision.json')
    for key in ('executed_postprocessor','revised_postprocessor'):
        if helper.digest(HERE/revision[key]) != revision[key+'_sha256']: errors.append('Postprocessor identity differs: '+key)
        compile((HERE/revision[key]).read_bytes(),str(HERE/revision[key]),'exec')
    source_files = ('scripts/raw_grid_segment.py','tests/test_raw_grid_segment.py')
    freeze = helper.read(HERE/'auxiliary_freeze.json')
    for name in source_files:
        actual = helper.digest(ROOT/name)
        committed = hashlib.sha256(subprocess.run(['git','show',freeze['auxiliary_content_commit']+':'+name],cwd=ROOT,capture_output=True,check=True).stdout).hexdigest()
        if actual != committed or actual != freeze['source_identity'][name]['executed_sha256']: errors.append('Auxiliary source identity differs')
    names = subprocess.run(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True).stdout.split(b'\0')
    untracked = [p.decode('utf-8') for p in names if p]
    session_relative = Path(plan['session_directory']).relative_to(ROOT).as_posix()
    batch_relative = HERE.relative_to(ROOT).as_posix()
    if any(not p.startswith((session_relative+'/',batch_relative+'/')) for p in untracked): errors.append('Out-of-scope untracked files')
    files = [ROOT/p for p in untracked] + [ROOT/p for p in
        subprocess.run(['git','diff','--name-only'],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()]
    secret = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}')
    big = []; binaries = []; leaks = []
    for p in files:
        if p.stat().st_size > 50*1024*1024: big.append(str(p.relative_to(ROOT)))
        if p.suffix.lower() in ('.exe','.o','.a','.so','.bin','.pyc'): binaries.append(str(p.relative_to(ROOT)))
        if secret.search(p.read_bytes()): leaks.append(str(p.relative_to(ROOT)))
    if big or binaries or leaks: errors.append('Large file / binary / credential scan failed')
    new_lines = subprocess.run(['git','diff','--unified=0','--','*.md'],cwd=ROOT,capture_output=True,check=True).stdout.decode()
    links = []; missing = []
    current = None
    for line in new_lines.splitlines():
        if line.startswith('+++ b/'): current = ROOT/line[6:]
        elif line.startswith('+') and not line.startswith('+++') and current:
            links.extend((current,x) for x in re.findall(r'\]\(([^)]+)\)',line[1:]))
    for p in [HERE/'README.md']:
        links.extend((p,x) for x in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')))
    for p,link in links:
        target = link.split('#')[0].strip('<>')
        if target and not re.match(r'^[a-zA-Z]+:',target) and not (p.parent/target).exists(): missing.append({'file':str(p.relative_to(ROOT)),'target':link})
    if missing: errors.append('New relative links missing')
    diffcheck = subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True)
    if diffcheck.returncode: errors.append('Git diff check failed')
    result = {'packaging_pass':not errors,'errors':errors,'source_sha256':helper.digest(Path(__file__)),
        'auxiliary_source_and_git_byte_identity_pass':not any('source identity' in e for e in errors),
        'postprocessor_executed_identity_pass':not any('Postprocessor' in e for e in errors),
        'checked_new_or_modified_files':len(files),'new_relative_links_checked':len(links),'missing_links':missing,
        'oversized_files':big,'binary_cache_files':binaries,'credential_pattern_files':leaks,
        'git_diff_check_returncode':diffcheck.returncode,'closed_operation_count':index['all_closed_operation_count'],
        'own_parent_pending_at_snapshot':index['own_parent_pending_at_snapshot'],
        'note':'Only independent read-only checks. No resource admission, native probe, matrix or search executed. Auxiliary cost index is closed again after this checker exits.'}
    f.atomic_write_json(HERE/'packaging_verification.json',result);print(json.dumps(result),flush=True)
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
