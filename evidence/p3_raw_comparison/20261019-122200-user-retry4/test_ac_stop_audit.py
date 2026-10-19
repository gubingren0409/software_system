"""Synthetic acceptance tests only; no power change, gate, clock or C invocation."""
import unittest
from summarize_continuation import check_ac_refusal_result

class ACRefusalAuditTests(unittest.TestCase):
    def fixture(self):
        return (dict(status='stopped',phase='preflight',failure_reason='AC power required; keep lid open',qpc_start=100,qpc_end=200,qpc_frequency=10),
            dict(returncode=2,timed_out=False,operation_kind='ac_status',qpc_start=120,qpc_end=150,qpc_frequency=10),
            dict(ok=True,ac=0,battery_percent=75))

    def test_valid_refusal_is_not_a_resource_or_clock_pass(self):
        w,o,a=self.fixture(); self.assertIsNone(check_ac_refusal_result(w,o,a))

    def test_wrong_or_nonfinite_status_rejected(self):
        for key,value in (('ac',1),('ac',False),('ok',False),('battery_percent',float('nan')),('battery_percent',-1)):
            w,o,a=self.fixture(); a[key]=value
            with self.assertRaises(ValueError): check_ac_refusal_result(w,o,a)

    def test_wrong_stage_timeout_returncode_or_qpc_binding_rejected(self):
        for key,value in (('returncode',0),('timed_out',True),('qpc_end',300),('qpc_frequency',20),('operation_kind','other')):
            w,o,a=self.fixture(); o[key]=value
            with self.assertRaises(ValueError): check_ac_refusal_result(w,o,a)
        w,o,a=self.fixture(); w['phase']='evaluation'
        with self.assertRaises(ValueError): check_ac_refusal_result(w,o,a)

if __name__=='__main__': unittest.main()
