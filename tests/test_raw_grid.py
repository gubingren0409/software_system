"""Controlled integration only: no 4096 execution, Grid or real clock probes."""
import copy,json,sys,tempfile,time,unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from autotuner.core import Config,TargetAdapter,sha256_file,sha256_json
from autotuner.measurement import ConfigurationEvaluator
from autotuner.session import restore_complete_group
from autotuner.timing import (FORMAL_RAW_VERSION,measurement_timing,relocate_target,
                              require_formal_activation,load_timing_binding)
from autotuner.raw_grid import accept_group
from scripts.raw_clock_contract import raw_schedule,require_certificate
from scripts.run_fixed_work_clock import send_request
from test_raw_timing import raw_result

ROOT=Path(__file__).resolve().parents[1]


class RawStub:
    def __init__(self,protocol):
        self.calls=[]
        self.target=SimpleNamespace(timing_protocol=measurement_timing(protocol,ROOT))
    def evaluate(self,config,context):
        i=len(self.calls); self.calls.append(context); parsed=raw_result()
        parsed.update(timing_protocol_version=FORMAL_RAW_VERSION,n=context.matrix_n,
            block_size=config.block_size,seed=context.seed,input=context.input_pattern,
            checked_entries=context.matrix_n**2)
        parsed['raw_end_ns']=parsed['raw_start_ns']+(i+1)*1_000_000_000
        parsed['elapsed_seconds']=float(i+1)
        parsed['monotonic_minus_raw_seconds']=parsed['monotonic_elapsed_seconds']-parsed['elapsed_seconds']
        return {'config':asdict(config),'run_id':str(i),'classification':'success','score_seconds':float(i+1),
            'source':'fresh_measurement','returncode':0,'timed_out':False,'raw_stdout':json.dumps(parsed),
            'target_result':parsed,'context':asdict(context),'process_wall_seconds':float(i+1)}


class RawGridTests(unittest.TestCase):
    def protocol(self):
        protocol=json.loads((ROOT/'configs/measurement_protocol.json').read_text())
        protocol['target_matrix_n']=130
        return protocol
    def grouped(self,directory):
        protocol=self.protocol(); stub=RawStub(protocol)
        with patch('autotuner.measurement.execution_clock',side_effect=lambda raw:time.perf_counter()):
            group=ConfigurationEvaluator(stub,protocol,sha256_json(protocol),directory).evaluate(Config('O2',8),attempt_id='controlled')
        return protocol,stub,group

    def test_relocated_target_binding_loads_outside_config_directory(self):
        data=json.loads((ROOT/'configs/target.json').read_text())
        expected=data['timing_protocol']['hash']; data['compiler']=sys.executable
        effective=relocate_target(data,ROOT/'configs')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unrelated-output'/'effective_target.json'; path.parent.mkdir()
            effective['cache_root']=str(Path(directory)/'local-cache')
            path.write_text(json.dumps(effective))
            adapter=TargetAdapter.load(path)
            self.assertEqual(adapter.timing_protocol,measurement_timing(self.protocol(),ROOT))
            self.assertEqual(adapter.config['timing_protocol']['hash'],expected)
            self.assertTrue(Path(adapter.config['timing_protocol']['file']).is_absolute())

    def test_raw_binding_missing_null_or_bad_rejected(self):
        for change in ('missing','null','hash','version'):
            protocol=self.protocol()
            if change=='missing': del protocol['timing_protocol']
            elif change=='null': protocol['timing_protocol']=None
            elif change=='hash': protocol['timing_protocol']['hash']='0'*64
            else: protocol['timing_protocol']={'file':'configs/raw_timing_protocol.json',
                     'hash':sha256_json(json.loads((ROOT/'configs/raw_timing_protocol.json').read_text()))}
            with self.assertRaises(ValueError): require_formal_activation(protocol,ROOT)
        for version in (0,7,True):
            protocol=self.protocol(); protocol['schema_version']=version
            with self.assertRaises(ValueError): measurement_timing(protocol,ROOT)

    def test_wrong_primary_clock_even_with_matching_file_hash_rejected(self):
        timing=json.loads((ROOT/'configs/raw_formal_timing_protocol.json').read_text()); timing['primary_clock']='CLOCK_MONOTONIC'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'timing.json'; path.write_text(json.dumps(timing))
            with self.assertRaises(ValueError): load_timing_binding({'file':str(path),'hash':sha256_json(timing)},ROOT)

    def test_raw_one_warmup_five_fresh_median_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            protocol,stub,group=self.grouped(Path(directory))
            self.assertEqual(len(stub.calls),6); self.assertTrue(all(c.force_remeasure for c in stub.calls))
            self.assertEqual(group['score_seconds'],4.0)
            self.assertEqual(group['measured_compute_seconds'],[2.,3.,4.,5.,6.])
            self.assertEqual(restore_complete_group(group,protocol),group)

    def test_partial_cache_bad_endpoint_cannot_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            protocol,_,original=self.grouped(Path(directory))
            for mode in ('partial','cache','endpoint'):
                group=copy.deepcopy(original)
                if mode=='partial': group['samples'].pop()
                elif mode=='cache': group['samples'][1]['source']='performance_cache'
                else:
                    sample=group['samples'][1]; sample['target_result']['raw_end_ns']=sample['target_result']['raw_start_ns']-1
                    sample['raw_stdout']=json.dumps(sample['target_result'])
                with self.assertRaises(ValueError): restore_complete_group(group,protocol)

    def test_missing_old_foreign_sha_or_session_certificate_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); initial=root/'initial.json'; initial.write_text('{}')
            plan={'content_commit':'a'*40,'session_id':'b'*32,'timing_protocol_hash':'c'*64,'measurement_protocol_hash':'d'*64}
            with self.assertRaises(OSError): require_certificate(root,plan,initial)
            manifest=root/'manifest.json'; manifest.write_text('{}'); checked={'recovery_eligible':True}
            cert={'schema':'raw-grid-recovery-certificate-v1',**plan,
                  'initial_checkpoint_sha256':sha256_file(initial),'manifest_sha256':sha256_file(manifest),'audit':checked}
            with patch('scripts.raw_clock_contract.audit_recovery',return_value=checked):
                for field,value in (('schema','old-mono'),('content_commit','f'*40),('session_id','f'*32),('audit',{'recovery_eligible':False})):
                    changed={**cert,field:value}; (root/'certificate.json').write_text(json.dumps(changed))
                    with self.assertRaises(ValueError): require_certificate(root,plan,initial)
                (root/'certificate.json').write_text(json.dumps(cert))
                self.assertEqual(require_certificate(root,plan,initial),checked)

    def test_group_after_clock_failure_does_not_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); protocol,_,group=self.grouped(root)
            path=root/'configurations/grid_controlled.json'; path.write_text(json.dumps(group))
            state={'completed':[],'active':{'attempt_id':'controlled'}}
            plan={'content_commit':'a'*40,'session_id':'b'*32,'session_directory':str(root)}
            with patch('autotuner.raw_grid.opened',return_value=(root,protocol,None,state)), \
                 patch('autotuner.raw_grid.audit_gate',return_value=True), \
                 patch('autotuner.raw_grid.audit_clock',side_effect=[{'evidence_integrity_pass':True,'raw_reference_pass':True},
                                                                   {'evidence_integrity_pass':True,'raw_reference_pass':False}]):
                with self.assertRaisesRegex(ValueError,'after RAW/QPC'): accept_group(plan,0,'controlled',str(root/'checks'))
            self.assertEqual(state['completed'],[]); self.assertIsNotNone(state['active'])

    def test_qpc_send_stamp_after_progress_before_write_flush(self):
        events=[]
        child=SimpleNamespace(stdin=SimpleNamespace(write=lambda data:events.append('write'),flush=lambda:events.append('flush')))
        def qpc(): events.append('qpc'); return 123,10
        with patch('scripts.run_fixed_work_clock.qpc',side_effect=qpc):
            self.assertEqual(send_request(child,'READ 2\n',lambda:events.append('progress')),(123,10))
        self.assertEqual(events,['progress','qpc','write','flush'])

    def test_exact_one_recovery_plan_default_path_fixed_work(self):
        rows=raw_schedule('recovery')
        self.assertEqual(len(rows),12); self.assertEqual([r['index'] for r in rows if r['long']],[5,11])
        self.assertEqual(sum(r['updates'] for r in rows),30_000_000_000)
        self.assertTrue(all(r['path']=='libc' and r['selected_cpu']==-1 for r in rows))
        self.assertEqual(len(raw_schedule('before')),1); self.assertEqual(len(raw_schedule('after')),1)

    def test_candidate_rejected_and_real_historical_protocol_supported(self):
        candidate={'schema_version':5,'timing_protocol':{'file':'configs/raw_timing_protocol.json',
                   'hash':sha256_json(json.loads((ROOT/'configs/raw_timing_protocol.json').read_text()))}}
        with self.assertRaisesRegex(ValueError,'candidate only'): require_formal_activation(candidate,ROOT)
        historical=json.loads((ROOT/'evidence/p3/campaign-e308bfb/protocol.json').read_text())
        self.assertIsNone(require_formal_activation(historical,ROOT))

    def test_new_session_initialization_never_builds_or_executes_matrix(self):
        from autotuner.raw_grid import initialize
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory); target=MagicMock(); compiler='c'*64
            plan={'session_directory':str(output),'session_id':'b'*32,'compiler_sha256':compiler}
            with patch('autotuner.raw_grid.runtime',return_value=(output,self.protocol(),target,{'compiler_sha256':compiler})):
                self.assertEqual(initialize(plan),0)
            target.build_candidate.assert_not_called(); target.get_reference.assert_not_called()
            state=json.loads((output/'checkpoint.json').read_text())
            self.assertEqual(state['completed'],[]); self.assertEqual(state['target_executions'],0)
            self.assertEqual(state['reference_generation_calls'],0)

    def test_unaccepted_after_check_is_independently_recomputed(self):
        from scripts.audit_raw_grid import audit_group_clock_inventory
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory); clock=output/'group_checks/attempt/after'; clock.mkdir(parents=True)
            (clock/'manifest.json').write_text(json.dumps({'context':{'config_index':0}}))
            measured=output/'configurations/grid_attempt.json'; measured.parent.mkdir(); measured.write_text('{}')
            plan={'content_commit':'a'*40,'session_id':'b'*32}
            with patch('scripts.audit_raw_grid.audit_clock',return_value={'evidence_integrity_pass':True,'raw_reference_pass':False}) as checked:
                batches=audit_group_clock_inventory(plan,output)
            self.assertEqual(len(batches),1); self.assertFalse(batches[0]['audit']['raw_reference_pass'])
            self.assertEqual(checked.call_args.args[1]['group_sha256'],sha256_file(measured))


if __name__=='__main__': unittest.main()
