"""RAW candidate contract and fail-closed admission; synthetic timing, no 4096."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from autotuner.core import Config,EvaluationContext,Evaluator,ConfigSpace,classify_execution,sha256_json
from autotuner.timing import (RAW_RESULT_SCHEMA,RAW_VERSION,check_raw_result,
    load_timing_binding,measurement_timing,require_formal_activation)
from test_runner import valid_result,FakeTarget

ROOT=Path(__file__).resolve().parents[1]


def raw_result():
    data=valid_result(); base=2**57+123
    data.update(schema=RAW_RESULT_SCHEMA,primary_clock='CLOCK_MONOTONIC_RAW',timing_protocol_version=RAW_VERSION,
        raw_start_ns=base,raw_end_ns=base+100_000_000,monotonic_start_ns=base-100,
        monotonic_end_ns=base+110_000_100,monotonic_elapsed_seconds=0.1100002,
        monotonic_minus_raw_seconds=0.1100002-0.1)
    return data


class RawTimingTests(unittest.TestCase):
    def classify(self,result,code=0): return classify_execution(code,False,json.dumps(result),RAW_RESULT_SCHEMA)[0]

    def test_precise_integer_subtraction_and_valid_success(self):
        self.assertEqual(self.classify(raw_result()),'success')
        check_raw_result(raw_result())

    def test_wrong_clock_or_version_never_scores(self):
        for field,value in (('primary_clock','CLOCK_MONOTONIC'),('timing_protocol_version','old')):
            data=raw_result(); data[field]=value
            self.assertEqual(self.classify(data),'validation_failure')

    def test_invalid_endpoints(self):
        for value in (0,-1,True,1.0,None,2**63):
            data=raw_result(); data['raw_start_ns']=value
            self.assertEqual(self.classify(data),'validation_failure')
        data=raw_result(); del data['raw_end_ns']
        self.assertEqual(self.classify(data),'validation_failure')

    def test_nonpositive_and_backward(self):
        for delta in (0,-1):
            data=raw_result(); data['raw_end_ns']=data['raw_start_ns']+delta
            self.assertEqual(self.classify(data),'validation_failure')

    def test_saved_delta_must_exactly_match(self):
        for key in ('elapsed_seconds','monotonic_elapsed_seconds','monotonic_minus_raw_seconds'):
            data=raw_result(); data[key]+=1e-9
            self.assertEqual(self.classify(data),'validation_failure')

    def test_aux_monotonic_difference_is_not_an_equality_gate(self):
        data=raw_result(); self.assertGreater(data['monotonic_minus_raw_seconds'],0.005)
        self.assertEqual(self.classify(data),'success')
        data['monotonic_end_ns']=data['monotonic_start_ns']-1000
        data['monotonic_elapsed_seconds']=-0.000001
        data['monotonic_minus_raw_seconds']=-0.000001-data['elapsed_seconds']
        self.assertEqual(self.classify(data),'success') # Explicitly preserved auxiliary rollback, not RAW rollback.

    def test_raw_failure_not_rescued_by_auxiliary(self):
        data=raw_result(); data['raw_end_ns']=data['raw_start_ns']-1
        self.assertNotEqual(self.classify(data),'success')

    def test_exit64_65_and_nonfinite_no_score(self):
        for code in (64,65): self.assertNotEqual(self.classify(raw_result(),code),'success')
        for field in ('elapsed_seconds','monotonic_elapsed_seconds','monotonic_minus_raw_seconds'):
            for value in (float('nan'),float('inf'),None):
                data=raw_result(); data[field]=value
                self.assertNotEqual(self.classify(data),'success')

    def test_legacy_result_still_uses_legacy_contract(self):
        self.assertEqual(classify_execution(0,False,json.dumps(valid_result()))[0],'success')
        self.assertNotEqual(self.classify(valid_result()),'success')
        self.assertNotEqual(classify_execution(0,False,json.dumps(raw_result()))[0],'success')

    def test_protocol_binding_and_admission_fail_closed(self):
        measurement=json.loads((ROOT/'configs/measurement_protocol.json').read_text())
        timing=measurement_timing(measurement,ROOT)
        self.assertEqual(timing['primary_clock'],'CLOCK_MONOTONIC_RAW')
        candidate={'schema_version':5,'timing_protocol':{'file':'configs/raw_timing_protocol.json',
            'hash':sha256_json(json.loads((ROOT/'configs/raw_timing_protocol.json').read_text()))}}
        with self.assertRaisesRegex(ValueError,'candidate only'): require_formal_activation(candidate,ROOT)
        legacy=json.loads((ROOT/'evidence/p3/campaign-e308bfb/protocol.json').read_text())
        self.assertIsNone(require_formal_activation(legacy,ROOT))
        broken=copy.deepcopy(measurement['timing_protocol']); broken['hash']='0'*64
        with self.assertRaises(ValueError): load_timing_binding(broken,ROOT)

    def test_same_protocol_in_target_and_measurement(self):
        target=json.loads((ROOT/'configs/target.json').read_text())
        measurement=json.loads((ROOT/'configs/measurement_protocol.json').read_text())
        self.assertEqual(load_timing_binding(target['timing_protocol'],ROOT/'configs'),measurement_timing(measurement,ROOT))
        self.assertEqual(len(set(ConfigSpace.load(ROOT/'configs/config_space.json').all())),20)

    @unittest.skipIf(sys.platform=='win32','POSIX process-group watchdog test')
    def test_raw_watchdog_timeout_keeps_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary); executable=path/'fake.py'
            executable.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(5)\n'); executable.chmod(0o755)
            target=FakeTarget(executable,path/'evidence','run')
            target.config['result_schema']=RAW_RESULT_SCHEMA
            target.timing_protocol=measurement_timing(json.loads((ROOT/'configs/measurement_protocol.json').read_text()),ROOT)
            target.config['timing_protocol']={'hash':'synthetic-watchdog-only'}
            record=Evaluator(target).evaluate(Config('O2',8),EvaluationContext(17,1,'random',0.05,'raw-timeout'))
            self.assertEqual(record['classification'],'timeout'); self.assertIsNone(record['score_seconds'])
            self.assertEqual(record['process_wall_clock'],'CLOCK_MONOTONIC_RAW')

    def test_recovery_entry_refuses_candidate_before_creating_output(self):
        if sys.platform!='win32': self.skipTest('Actual Windows entry')
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'must-not-exist'
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'scripts/start_p3_first_seed.py'),
                '--mode','recover','--content-sha','a'*40,'--auxiliary-sha','a'*40,
                '--archive-directory','/var/tmp/not-used','--campaign-directory',str(output/'campaign'),
                '--git-identity',str(output/'identity.json'),'--session-id','b'*32,'--output',str(output)],
                cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0); self.assertIn('Formal RAW Grid uses',result.stderr)
            self.assertFalse(output.exists())


if __name__=='__main__': unittest.main()
