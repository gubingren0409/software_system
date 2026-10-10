"""Evidence-only command capture and frozen-content export; not a search runner."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import capture, atomic_write_json, snapshot_campaign, POWERSHELL, load
from autotuner.core import sha256_file, sha256_json, utc_now


def run(name, command, timeout=120):
    result = capture(command, HERE, name, HERE.name, timeout=timeout)
    print(json.dumps({'operation': name, 'returncode': result['returncode'], 'qpc_seconds': result['qpc_seconds']}), flush=True)
    return result


def wsl(code):
    return ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', '/tmp', '--', 'env', '-u', 'PYTHONPATH',
            'PYTHONDONTWRITEBYTECODE=1', 'python3', '-c', code]


if __name__ == '__main__':
    phase = sys.argv[1]
    if phase == 'before':
        for name, command in [('status_before',['git','status','--short']), ('head_before',['git','rev-parse','HEAD']),
                              ('branch_before',['git','branch','--show-current']), ('remote_before',['git','remote','-v'])]:
            assert run(name,command)['returncode']==0
        assert run('base_ancestor',['git','merge-base','--is-ancestor','ac33d9d897b4f3802251430956ae79fb4e4a49a8','HEAD'])['returncode']==0
        for name, path in [('legacy_e308bfb',ROOT/'evidence/p3/campaign-e308bfb'),
                           ('sealed_7405fcc3',ROOT/'evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3')]:
            atomic_write_json(HERE/(name+'_before.json'), snapshot_campaign(path))
        old=load(ROOT/'evidence/p3_resource_policy/20261010-161312-30f9a2a1-recovery-7405fcc3/resources.stdout.txt')
        assert old['host_minimum_available_bytes']==775036928 and old['wsl_available_bytes']==6208774144
        assert old['rejection_reasons']==['host_memory']
        atomic_write_json(HERE/'declaration.json', {'declared_at':utc_now(),'baseline':'ac33d9d897b4f3802251430956ae79fb4e4a49a8',
            'diagnostic_groups':1,'recovery_call_limit':1,'prior_clock_intervals':0,'prior_target_executions':0,
            'diagnostic_source_sha256':sha256_file(HERE/'diagnose.ps1'), 'orchestration_source_sha256':sha256_file(Path(__file__)),
            'prior_resource_sha256':sha256_file(ROOT/'evidence/p3_resource_policy/20261010-161312-30f9a2a1-recovery-7405fcc3/resources.stdout.txt'),
            'no_cold_boot_capture':True,'no_system_changes':True})
        for prefix in ('code/original','evidence/p2','evidence/p3','evidence/p3_clock_repair','evidence/p3_clock_contract','evidence/p3_resource_policy'):
            paths=subprocess.check_output(['git','ls-files','--',prefix],cwd=ROOT,text=True).splitlines()
            identities={path:sha256_file(ROOT/path) for path in paths}
            atomic_write_json(HERE/(prefix.replace('/','_')+'_protected.json'), {'prefix':prefix,'count':len(paths),'raw_map_sha256':sha256_json(identities)})
    elif phase == 'diagnose':
        result=run('paired_memory_diagnosis',[POWERSHELL,'-NoProfile','-File',str(HERE/'diagnose.ps1')],timeout=120)
        raise SystemExit(result['returncode'] if type(result['returncode']) is int else 1)
    elif phase == 'prevalidate':
        assert run('windows_resource_tests',[sys.executable,'-B','-X','utf8','-m','unittest','discover','-s','tests','-p','test_resource_policy.py','-v'],timeout=180)['returncode']==0
        command=['wsl.exe','-d','Ubuntu-24.04','--cd','/mnt/e/software_system/project01','--','env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',
                 'python3','-m','unittest','discover','-s','tests','-p','test_resource_policy.py','-v']
        assert run('wsl_resource_tests',command)['returncode']==0
        assert run('actual_resource_capture',[POWERSHELL,'-NoProfile','-File',str(ROOT/'scripts/check_p2_resources.ps1'),
                 '-Mode','Recovery','-RuntimeRoot','/mnt/e/software_system/project01'],timeout=90)['returncode'] in (0,2)
        result=load(HERE/'actual_resource_capture.stdout.txt')
        from autotuner.resources import judge,load_policy
        assert judge(result,load_policy(ROOT/'configs/resource_policy.json'),'Recovery',sha256_file(ROOT/'configs/resource_policy.json'))==result
        command = "$p=Join-Path ([Environment]::GetFolderPath('UserProfile')) '.wslconfig'; if (Test-Path -LiteralPath $p) { [pscustomobject]@{sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash; relevant_lines=@(Get-Content -LiteralPath $p | Where-Object {$_ -match '^\\s*(\\[wsl2\\]|\\[experimental\\]|memory\\s*=|autoMemoryReclaim\\s*=|pageReporting\\s*=|swap\\s*=)'})} | ConvertTo-Json } else { 'unknown: .wslconfig absent' }"
        run('existing_wslconfig',[POWERSHELL,'-NoProfile','-Command',command],timeout=30)
        run('wsl_version',['wsl.exe','--version'],timeout=30)
    else:
        raise ValueError('Unknown phase')
