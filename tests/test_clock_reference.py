"""Controlled integer endpoints only; no real diagnostic intervals."""
import unittest
from pathlib import Path

from scripts.p3_clock_reference import CONDITIONS,check_interval


def fixture():
    base=2**60+117
    def response(seq,op):
        return {'schema':'native-clock-endpoint-v1','op':op,'pid':72,'seq':seq,'path':'libc','selected_cpu':-1}
    def read(seq,position):
        endpoint=response(seq,'READ')
        endpoint.update({key:base+position for key in ('m1_ns','raw_ns','m2_ns','realtime_ns','boottime_ns')})
        endpoint.update(m2_ns=base+position+120,cpu_before=0,cpu_after=1)
        return {'command':f'READ {seq}\n','send_qpc':base+position-100_000,
                'recv_qpc':base+position+100_000,'response':endpoint}
    wait=response(2,'WAIT'); wait.update(workload='idle',work_checksum=2**64-1)
    return {'schema':'qpc-bounded-clock-interval-v1','condition':'A','index':0,'selected_cpu':-1,
            'start':read(1,0),'end':read(3,3_000_000_000),
            'wait':{'command':'WAIT 2 idle\n','send_qpc':base+200_000,
                    'recv_qpc':base+2_999_800_000,'response':wait}}


class ClockReferenceTests(unittest.TestCase):
    def check(self,row): return check_interval(row,1_000_000_000,CONDITIONS[0],72,1,[0,1])
    def test_normal_and_integer_precision(self):
        row=fixture(); checked=self.check(row)
        self.assertTrue(checked['reference_match_pass'])
        self.assertEqual(checked['guest_durations_ns']['monotonic_high_ns'],3_000_000_120)
        row['end']['response']['raw_ns']+=1
        self.assertEqual(self.check(row)['guest_durations_ns']['raw_ns'],3_000_000_001)
    def test_wide_boundaries_indeterminate_not_filtered(self):
        row=fixture(); row['start']['send_qpc']-=30_000_000
        checked=self.check(row)
        self.assertTrue(checked['evidence_integrity_pass'])
        self.assertFalse(checked['reference_determinate']); self.assertFalse(checked['reference_match_pass'])
    def test_real_monotonic_mismatch_is_rejected(self):
        row=fixture()
        for key in ('m1_ns','m2_ns'): row['end']['response'][key]+=100_000_000
        self.assertFalse(self.check(row)['reference_match_pass'])
    def test_raw_warning_not_a_proof_of_monotonic(self):
        row=fixture(); row['end']['response']['raw_ns']+=100_000_000
        checked=self.check(row)
        self.assertTrue(checked['reference_match_pass']); self.assertFalse(checked['raw_within_host'])
        row['end']['response']['m1_ns']+=100_000_000; row['end']['response']['m2_ns']+=100_000_000
        self.assertFalse(self.check(row)['reference_match_pass'])
    def test_missing_and_out_of_order_or_changed_pid(self):
        mutations=[lambda r:r.pop('end'),lambda r:r['end']['response'].update(seq=4),
            lambda r:r['end']['response'].update(pid=73),
            lambda r:r['wait']['response'].update(workload='busy'),
            lambda r:r['wait'].update(send_qpc=r['start']['send_qpc']-1)]
        for mutate in mutations:
            row=fixture(); mutate(row)
            self.assertFalse(self.check(row)['evidence_integrity_pass'])
    def test_backwards_clock_and_host_rejected(self):
        for field in ('m1_ns','raw_ns','m2_ns','realtime_ns','boottime_ns'):
            row=fixture(); row['end']['response'][field]=row['start']['response'][field]-1
            self.assertFalse(self.check(row)['reference_match_pass'])
        row=fixture(); row['end']['send_qpc']=row['start']['send_qpc']-1
        self.assertFalse(self.check(row)['reference_match_pass'])
    def test_invalid_nonfinite_or_float_integer(self):
        for value in (None,True,0,-1,1.5,float('nan'),float('inf'),'3000000000'):
            row=fixture(); row['end']['response']['raw_ns']=value
            self.assertFalse(self.check(row)['evidence_integrity_pass'])
    def test_direct_or_pinned_does_not_certify_default_condition(self):
        row=fixture(); row['start']['response']['path']='syscall'
        self.assertFalse(self.check(row)['reference_match_pass'])
        row=fixture(); row['selected_cpu']=0
        self.assertFalse(self.check(row)['reference_match_pass'])
    def test_read_span_and_exact_uncertainty_boundary(self):
        row=fixture(); row['end']['response']['m2_ns']+=20_000_001
        self.assertFalse(self.check(row)['reference_determinate'])
        row=fixture(); row['start']['send_qpc']-=19_600_000
        self.assertTrue(self.check(row)['reference_determinate'])
        row['start']['send_qpc']-=1
        self.assertFalse(self.check(row)['reference_determinate'])
    def test_saved_pass_cannot_override_actual_mismatch(self):
        # Audit requires saved checks to equal the recomputation; a claimed PASS
        # cannot change this original endpoint-derived result.
        row=fixture(); row['check']={'reference_match_pass':True}
        for key in ('m1_ns','m2_ns'): row['end']['response'][key]+=100_000_000
        self.assertFalse(self.check(row)['reference_match_pass'])
        self.assertNotEqual(row['check'],self.check(row))
    def test_original_twenty_intervals_keep_six_failures(self):
        from scripts.p3_clock_contract import check_clock_intervals,load
        root=Path(__file__).resolve().parents[1]
        old=root/'evidence/p3_memory_policy/20261010-174802-11f7775c/recovery'
        criteria=load(root/'configs/timing_audit_protocol.json')['diagnostic_criteria']
        checked=[check_clock_intervals(load(old/(name+'.wsl.json')),criteria,10) for name in ('window_A','window_B')]
        self.assertTrue(all(item['evidence_integrity_pass'] for item in checked))
        self.assertEqual(sum(not row['monotonic_raw_pass'] for group in checked for row in group['checks']),6)
        self.assertTrue(all(not item['timing_checks_pass'] for item in checked))


if __name__=='__main__': unittest.main()
