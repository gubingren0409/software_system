"""Controlled continuation tests: no native probes, compiler or matrix execution."""
import copy
import importlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import raw_grid_segment as segment


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')


class SegmentTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / 'window'; directory.mkdir()
        session = root / 'session'; session.mkdir()
        (session / 'group_checks').mkdir()
        (directory / 'preserved').mkdir()
        write(directory / 'preserved/controller.json', {'qpc_frequency': 1000000000, 'updated_at': '2026-10-10T00:00:00+00:00'})
        write(session / 'controller.json', {'status': 'old-window-expired', 'total_qpc_seconds': segment.FIRST_SECONDS})
        write(session / 'initial_checkpoint.json', {'initial': True})
        state = {'session_id': segment.SESSION,
            'completed': [{'config': {'optimization': 'O0', 'block_size': s}, 'attempt_id': str(s)} for s in (8,16,24,64,128)],
            'active': None, 'abandoned_attempts': [], 'target_executions': 30, 'artifacts': {'reference': 'unchanged'},
            'reference_generation_calls': 1, 'setup_seconds': 1.0}
        write(session / 'checkpoint.json', state)
        records = [{'run_id': str(i)} for i in range(30)]
        (session / 'samples.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
        recovery = root / 'first-recovery'; recovery.mkdir(); write(recovery / 'certificate.json', {'first': True})
        plan = {'content_commit': segment.CONTENT, 'session_id': segment.SESSION,
            'session_directory': str(session), 'recovery_directory': str(recovery)}
        plan_path = root / 'plan.json'; write(plan_path, plan)
        auth = {'schema': segment.VERSION, 'helper_sha256': segment.digest(segment.SELF),
            'content_commit': segment.CONTENT, 'session_id': segment.SESSION, 'directory': str(directory),
            'plan_file': str(plan_path), 'plan_sha256': segment.digest(plan_path), 'start_index': 5, 'stop_index': 20,
            'performance_cache_allowed': False, 'new_window_seconds': 14400, 'cumulative_active_ceiling_seconds': 28800,
            'first_segment_qpc_seconds': segment.FIRST_SECONDS, 'start_checkpoint_sha256': segment.digest(session/'checkpoint.json'),
            'protected_session_files': {name: segment.digest(session/name) for name in ('controller.json','initial_checkpoint.json')},
            'first_recovery_sha256': {'certificate.json': segment.digest(recovery/'certificate.json')}, 'cached_manifest_sha256': {},
            'samples_prefix_bytes': (session/'samples.jsonl').stat().st_size, 'samples_prefix_sha256': segment.digest(session/'samples.jsonl'),
            'accepted_group_sha256': [segment.hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest() for g in state['completed']],
            'original_setup': {k: state[k] for k in ('artifacts','reference_generation_calls','setup_seconds')}}
        auth_path = directory/'authorization.json'; write(auth_path, auth)
        return auth_path, auth, plan, state, records

    def test_exact_five_group_start_and_unique_thirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,_,state,records = self.fixture(Path(tmp))
            segment.validate_start(state, records)
            for kind in ('wrong_config','active','abandoned','duplicate'):
                s,r = copy.deepcopy(state),copy.deepcopy(records)
                if kind=='wrong_config': s['completed'][4]['config']['optimization']='O1'
                if kind=='active': s['active']={'attempt': 'partial'}
                if kind=='abandoned': s['abandoned_attempts']=[{}]
                if kind=='duplicate': r[-1]=r[0]
                with self.assertRaises(ValueError): segment.validate_start(s,r)

    def test_single_claim_cannot_reset_four_hour_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'claim.json'; original={'qpc_start': 123,'authorization_sha256': 'a'*64}
            segment.exclusive_claim(path, original)
            with self.assertRaises(FileExistsError): segment.exclusive_claim(path, {'qpc_start': 456})
            self.assertEqual(segment.read(path), original)

    def test_different_epochs_add_verified_durations_only(self):
        first = segment.elapsed(10000, 13000, 100, 100)
        second = segment.elapsed(200, 600, 10, 10)
        self.assertEqual(segment.active_cost(first, second), 70)
        for args in ((10000, 100,100,100),(100,200,100,10),(True,200,100,100)):
            with self.assertRaises(ValueError): segment.elapsed(*args)
        with self.assertRaises(ValueError): segment.active_cost(segment.FIRST_SECONDS,14401)
        with self.assertRaises(ValueError): segment.active_cost(20000,10000)

    def test_identity_clock_and_formal_all_required(self):
        segment.require_admission(True,True,True)
        for flags in ((False,True,True),(True,False,True),(True,True,False),(True,True,None),(1,True,True)):
            with self.assertRaises(ValueError): segment.require_admission(*flags)

    def test_old_files_and_original_byte_prefix_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,auth,plan,_,_ = self.fixture(Path(tmp)); session=Path(plan['session_directory'])
            segment.verify_protection(auth,plan,initial=True)
            original=(session/'samples.jsonl').read_bytes()
            with (session/'samples.jsonl').open('ab') as stream: stream.write(b'{"run_id":"new"}\n')
            segment.verify_protection(auth,plan)
            (session/'samples.jsonl').write_bytes(original.replace(b'"0"',b'"X"',1))
            with self.assertRaisesRegex(ValueError,'byte prefix'): segment.verify_protection(auth,plan)
            (session/'samples.jsonl').write_bytes(original)
            write(session/'controller.json', {'status': 'overwritten'})
            with self.assertRaisesRegex(ValueError,'Historical'): segment.verify_protection(auth,plan)

    def test_five_groups_and_setup_costs_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,auth,plan,state,_ = self.fixture(Path(tmp))
            state['setup_seconds']=2.0; write(Path(plan['session_directory'])/'checkpoint.json', state)
            with self.assertRaisesRegex(ValueError,'groups/setup'): segment.verify_protection(auth,plan)

    def manual_fixture(self, auth_path, auth, plan):
        root=Path(plan['session_directory']).parent
        prior_dir=root/'prior/window'; prior_auth=prior_dir/'authorization.json'
        old=copy.deepcopy(auth); old['directory']=str(prior_dir); write(prior_auth,old)
        claim={'schema':segment.VERSION,'qpc_start':100_000_000_000,'qpc_frequency':10_000_000,
            'authorization_sha256':segment.digest(prior_auth),'helper_sha256':'b'*64,'auxiliary_content_commit':'c'*40}
        claim_path=Path(plan['session_directory'])/'RAW_SEGMENT_WINDOW_V1.claim.json'; write(claim_path,claim)
        window={**claim,'qpc_end':101_333_351_975,'status':'partial_or_blocked','budget_pass':True,
            'formal_invoked':False,'pre_resource_pass':False,'continuation_clock_pass':False,
            'window_qpc_seconds':segment.PRIOR_USED_SECONDS,
            'cumulative_active_qpc_seconds':segment.FIRST_SECONDS+segment.PRIOR_USED_SECONDS,
            'ended_at':'2026-10-12T00:00:00+00:00'}
        prior_window=prior_dir/'window.json'; write(prior_window,window)
        auth.update(schema=segment.MANUAL_VERSION,repository_directory=str(root),
            prior_authorization_file=str(prior_auth),prior_window_file=str(prior_window),prior_claim_file=str(claim_path),
            prior_delivery_commit=segment.MANUAL_BASELINE,prior_used_seconds=segment.PRIOR_USED_SECONDS,
            remaining_allowance_seconds=segment.REMAINING_SECONDS,manual_attempt_limit=1,
            protected_previous_files={str(p):segment.digest(p) for p in (prior_auth,prior_window,claim_path)})
        write(auth_path,auth)
        def git_show(argv,**kwargs):
            return SimpleNamespace(stdout=(root/argv[-1].split(':',1)[1]).read_bytes())
        return git_show

    def controlled_run(self, root, *, resource=True, clock=True, identity=True, manual=False):
        auth_path,auth,plan,state,_=self.fixture(root); session=Path(plan['session_directory']); commands=[]
        git_show=self.manual_fixture(auth_path,auth,plan) if manual else None
        def capture(argv,directory,name,*args,**kwargs):
            commands.append((name,argv))
            if name=='windows_environment':
                write(directory/(name+'.stdout.txt'), {'windows_boot_utc':'2026-10-12T00:00:00Z','at':'2026-10-12T01:00:00+00:00'})
            elif name=='wsl_environment': write(directory/(name+'.stdout.txt'), {'boot_id':'controlled'})
            else:
                index=int(argv[argv.index('--index')+1]); attempt=argv[argv.index('--attempt-id')+1]
                if name.startswith('measure_'): write(session/'configurations'/('grid_'+attempt+'.json'), {'fixture': True})
                elif name.startswith('accept_'):
                    self.assertEqual(index,len(state['completed']))
                    state['completed'].append({'config': {'optimization': 'O'+str(index//5), 'block_size': (8,16,24,64,128)[index%5]}, 'attempt_id':attempt})
                    write(session/'checkpoint.json',state)
            return {'returncode':0,'timed_out':False}
        f=SimpleNamespace(qpc=lambda:(time.perf_counter_ns(),1000000000),atomic_write_json=write,
            utc_now=lambda:'controlled',POWERSHELL='fake-powershell',linux=lambda p,args:args,
            wsl_path=str,capture=capture,gate=lambda *a:resource,collect_check=lambda *a:None)
        clock_call=unittest.mock.Mock()
        def verify(*a):
            if not identity: raise ValueError('Controlled helper identity mismatch')
        with patch.object(segment,'frozen',return_value=f), patch.object(segment,'verify_auxiliary',side_effect=verify), \
                patch.object(segment.subprocess,'run',side_effect=git_show), \
                patch.object(segment,'collect_admission',clock_call), \
                patch.object(segment,'audit_admission',return_value={'eligible':clock,'errors':[]}), \
                patch('scripts.audit_raw_grid.audit_grid',return_value={'evidence_integrity_pass':True,'errors':[]}):
            if not identity:
                with self.assertRaisesRegex(ValueError,'identity'): segment.run(auth_path,'a'*40)
                rc=None
            else: rc=segment.run(auth_path,'a'*40)
        return rc,commands,clock_call,state,auth,plan

    def test_manual_resume_deducts_prior_cost_and_preserves_original_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,commands,clock_call,state,auth,plan=self.controlled_run(Path(tmp),manual=True)
            self.assertEqual(rc,0); self.assertEqual(len(state['completed']),20); clock_call.assert_called_once()
            self.assertEqual([int(a[a.index('--index')+1]) for n,a in commands if n.startswith('measure_')],list(range(5,20)))
            window=segment.read(Path(auth['directory'])/'window.json')
            self.assertEqual(window['prior_used_seconds'],133.3351975)
            self.assertEqual(window['remaining_allowance_seconds'],14266.6648025)
            self.assertEqual(window['second_window_activity_seconds'],133.3351975+window['window_qpc_seconds'])
            self.assertEqual(window['cumulative_active_qpc_seconds'],segment.FIRST_SECONDS+(133.3351975+window['window_qpc_seconds']))
            original=Path(auth['prior_claim_file']); self.assertEqual(segment.digest(original),auth['protected_previous_files'][str(original)])
            manual_claim=Path(plan['session_directory'])/'RAW_SEGMENT_MANUAL_REMAINING_V1.claim.json'
            self.assertTrue(manual_claim.exists())
            with self.assertRaises(FileExistsError): segment.exclusive_claim(manual_claim,{'qpc_start':1})

    def test_manual_authorization_cannot_reset_or_discard_consumed_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,auth,plan,_,_=self.fixture(Path(tmp)); git_show=self.manual_fixture(path,auth,plan)
            with patch.object(segment.subprocess,'run',side_effect=git_show):
                self.assertEqual(segment.budget_settings(auth,plan)[:2],(133.3351975,14266.6648025))
                for key,value in (('prior_used_seconds',0),('remaining_allowance_seconds',14400),('manual_attempt_limit',2),('new_window_seconds',28800)):
                    wrong=copy.deepcopy(auth); wrong[key]=value
                    with self.assertRaises(ValueError): segment.budget_settings(wrong,plan)

    def test_manual_closed_attempt_must_match_hashes_and_audited_git_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,auth,plan,_,_=self.fixture(Path(tmp)); git_show=self.manual_fixture(path,auth,plan)
            old_path=Path(auth['prior_window_file']); saved=old_path.read_bytes()
            old=segment.read(old_path); old['formal_invoked']=True; write(old_path,old)
            with self.assertRaisesRegex(ValueError,'closed attempt changed'): segment.verify_previous(auth,plan)
            auth['protected_previous_files'][str(old_path)]=segment.digest(old_path)
            with self.assertRaisesRegex(ValueError,'claim/window'): segment.verify_previous(auth,plan)
            old_path.write_bytes(saved); auth['protected_previous_files'][str(old_path)]=segment.digest(old_path)
            with patch.object(segment.subprocess,'run',return_value=SimpleNamespace(stdout=b'wrong audited bytes')):
                with self.assertRaisesRegex(ValueError,'audited 9f'): segment.verify_previous(auth,plan)

    def test_manual_resource_failure_never_starts_clock_or_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,commands,clock_call,state,auth,_=self.controlled_run(Path(tmp),manual=True,resource=False)
            self.assertEqual(rc,2); clock_call.assert_not_called(); self.assertEqual(len(state['completed']),5)
            self.assertEqual(len(commands),2)
            self.assertGreater(segment.read(Path(auth['directory'])/'window.json')['second_window_activity_seconds'],133.3351975)

    def test_manual_clock_failure_never_starts_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,commands,clock_call,state,_,_=self.controlled_run(Path(tmp),manual=True,clock=False)
            self.assertEqual(rc,2); clock_call.assert_called_once(); self.assertEqual(len(state['completed']),5)
            self.assertEqual(len(commands),2)

    def test_controlled_resume_starts_index5_preserves_five_and_skips_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,commands,_,state,auth,plan=self.controlled_run(Path(tmp))
            self.assertEqual(rc,0); self.assertEqual(len(state['completed']),20)
            measured=[argv for name,argv in commands if name.startswith('measure_')]
            self.assertEqual([int(a[a.index('--index')+1]) for a in measured],list(range(5,20)))
            self.assertEqual(sum(name.startswith('accept_') for name,_ in commands),15)
            self.assertFalse(any('setup' in name for name,_ in commands))
            segment.verify_protection(auth,plan)

    def test_preflight_resource_failure_prevents_clock_and_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,commands,clock_call,_,_,_=self.controlled_run(Path(tmp),resource=False)
            self.assertEqual(rc,2); clock_call.assert_not_called()
            self.assertEqual([name for name,_ in commands],['windows_environment','wsl_environment'])

    def test_failed_clock_prevents_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,commands,clock_call,_,_,_=self.controlled_run(Path(tmp),clock=False)
            self.assertEqual(rc,2); clock_call.assert_called_once()
            self.assertEqual(len(commands),2)

    def test_wrong_auxiliary_identity_prevents_window_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,commands,clock_call,_,_,plan=self.controlled_run(Path(tmp),identity=False)
            self.assertFalse(commands); clock_call.assert_not_called()
            self.assertFalse((Path(plan['session_directory'])/'RAW_SEGMENT_WINDOW_V1.claim.json').exists())

    def test_expired_legacy_controller_not_reused_as_new_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_path,auth,plan,_,_=self.fixture(Path(tmp))
            auth['new_window_seconds']=28800; write(auth_path,auth)
            with patch.object(segment,'frozen',return_value=SimpleNamespace()), \
                    patch.object(segment,'verify_auxiliary') as verify:
                with self.assertRaisesRegex(ValueError,'Authorization'): segment.run(auth_path,'a'*40)
                verify.assert_not_called()
            self.assertFalse((Path(plan['session_directory'])/'RAW_SEGMENT_WINDOW_V1.claim.json').exists())

    def test_admission_recomputed_mismatch_and_wide_boundary_reject(self):
        # Same immutable integer checker used by the independent continuation audit.
        from test_fixed_work_clock import fixture
        from scripts.p3_fixed_work_clock import check_interval
        row=fixture(); plan=segment.admission_schedule()[0]; row['planned']=plan
        self.assertTrue(check_interval(row,10**9,plan,100,2,list(range(32)))['raw_pass'])
        row['check']={'raw_pass':True}
        for key in ('raw1_ns','raw2_ns'): row['end']['response'][key]+=100_000_000
        self.assertFalse(check_interval(row,10**9,plan,100,2,list(range(32)))['raw_pass'])
        row=fixture(); row['planned']=plan; row['end']['recv_qpc']+=21_000_000
        self.assertFalse(check_interval(row,10**9,plan,100,2,list(range(32)))['reference_determinate'])

    def test_exact_two_interval_schedule_and_no_old_recovery(self):
        schedule=segment.admission_schedule()
        self.assertEqual([r['updates'] for r in schedule],[10**9,10**10])
        self.assertTrue(all(r['path']=='libc' and r['selected_cpu']==-1 for r in schedule))
        self.assertEqual(len(schedule),2)

    def admission_fixture(self, root):
        from test_fixed_work_clock import fixture
        from scripts.p3_fixed_work_clock import check_interval
        _,auth,plan,_,_=self.fixture(root); directory=root/'admission'; directory.mkdir()
        binary=root/'probe'; binary.write_bytes(b'controlled-not-executable')
        build={'binary':str(binary),'binary_sha256':segment.digest(binary)}
        plan.update(allowed_cpus=list(range(32)), windows_source_identity={'probe.c':{'executed_sha256':'a'*64}},
                    probe_build_manifest=str(root/'build.json'))
        write(root/'build.json',build)
        f=SimpleNamespace(validate_plan=lambda p:({}, {'admission':{'original':'unchanged'}}),
            linux=lambda p,args:args,local_path=Path)
        base=fixture()['start']['send_qpc']; messages=[]; intervals=[]
        def endpoint(seq,op,send,**extra):
            return {'command':f'{op} {seq}\n','send_qpc':send,'recv_qpc':send+1000,
                'response':{'schema':'fixed-work-clock-endpoint-v1','op':op,'seq':seq,'pid':100,**extra}}
        messages.append(endpoint(0,'HELLO',base-400000,allowed_cpus=plan['allowed_cpus']))
        messages[0]['command']='START_PROCESS'
        for index,planned in enumerate(segment.admission_schedule()):
            row=fixture(); row['planned']=planned; pointer=index*4+1; shift=index*5_000_000_000
            mode=endpoint(pointer,'MODE',base+shift-200000,path='libc',selected_cpu=-1)
            mode['command']=f'MODE {pointer} libc -1\n'; messages.append(mode)
            for key,seq in (('start',pointer+1),('work',pointer+2),('end',pointer+3)):
                msg=row[key]; msg['send_qpc']+=shift; msg['recv_qpc']+=shift; msg['response']['seq']=seq
                if key=='work':
                    msg['response']['executed_updates']=planned['updates']; msg['command']=f"WORK {seq} {planned['updates']}\n"
                else:
                    msg['command']=f'READ {seq}\n'
                    for field in ('m1_ns','raw1_ns','monotonic_ns','raw2_ns','m2_ns','realtime_ns','boottime_ns'):
                        msg['response'][field]+=shift
                messages.append(msg)
            row['check']=check_interval(row,10**9,planned,100,pointer+1,plan['allowed_cpus']); intervals.append(row)
        messages.append(endpoint(9,'QUIT',base+9_000_000_000))
        manifest={'schema':'raw-grid-segment-admission-v1','content_commit':segment.CONTENT,'session_id':segment.SESSION,
            'authorization_sha256':segment.digest(Path(auth['directory'])/'authorization.json'),
            'checkpoint_sha256':auth['start_checkpoint_sha256'],'auxiliary_sha256':segment.digest(segment.SELF),
            'criteria':f.validate_plan(plan)[1]['admission'],'schedule':segment.admission_schedule(),
            'collection_budget_seconds':120,'allowed_cpus':plan['allowed_cpus'],
            'source_sha256':{'probe.c':'a'*64},'probe_build':build,'command':segment.admission_command(f,plan,build)}
        write(directory/'manifest.json',manifest)
        op={'schema':'raw-grid-segment-clock-process-v1','command':manifest['command'],
            'hello':messages[0]['response'],'returncode':0,'errors':[],
            'qpc_start':base-500000,'qpc_end':base+9_001_000_000,'qpc_frequency':10**9,
            'qpc_seconds':9.0015,'manifest_sha256':segment.digest(directory/'manifest.json')}
        def save():
            for name,data in (('messages.jsonl',messages),('intervals.jsonl',intervals),('native.stdout.txt',[m['response'] for m in messages])):
                (directory/name).write_text(''.join(json.dumps(row)+'\n' for row in data))
            (directory/'native.stderr.txt').write_bytes(b'')
            op['stream_sha256']={name:segment.digest(directory/name) for name in ('messages.jsonl','intervals.jsonl','native.stdout.txt','native.stderr.txt')}
            write(directory/'process.json',op)
        save()
        return f,plan,auth,directory,intervals,messages,op,save

    def test_independent_admission_checks_original_endpoints_not_saved_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            f,p,a,d,intervals,_,_,save=self.admission_fixture(Path(tmp))
            self.assertTrue(segment.audit_admission(f,p,a,d)['eligible'])
            for key in ('raw1_ns','raw2_ns'): intervals[0]['end']['response'][key]+=100_000_000
            save()
            checked=segment.audit_admission(f,p,a,d)
            self.assertFalse(checked['eligible']); self.assertIn('contradicts',str(checked['errors']))

    def test_partial_or_unhashed_admission_never_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            f,p,a,d,intervals,_,op,save=self.admission_fixture(Path(tmp))
            intervals.pop(); save()
            self.assertFalse(segment.audit_admission(f,p,a,d)['eligible'])
            del op['stream_sha256']['native.stderr.txt']; write(d/'process.json',op)
            self.assertFalse(segment.audit_admission(f,p,a,d)['eligible'])


if __name__=='__main__': unittest.main()
