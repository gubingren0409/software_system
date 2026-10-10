import copy
import unittest
from scripts.p3_fixed_work_clock import schedule,check_interval


def fixture():
    plan=schedule(17)[0]; freq=1_000_000_000; base=2**57+123
    def read(seq,send,guest):
        return {'command':f'READ {seq}\n','send_qpc':send,'recv_qpc':send+100_000,'response':{
            'schema':'fixed-work-clock-endpoint-v1','op':'READ','pid':100,'seq':seq,'path':'libc','selected_cpu':-1,
            'm1_ns':guest,'raw1_ns':guest+100,'monotonic_ns':guest+150,'raw2_ns':guest+200,'m2_ns':guest+300,
            'realtime_ns':guest+10**15,'boottime_ns':guest,'cpu_before':1,'cpu_after':2,
            'adjtimex':{'modes':0,'status':'unknown'},'boot_id':'unknown','uptime':'unknown','clocksource':'unknown'}}
    start=read(2,base,base+50_000); end=read(4,base+3_000_000_000,base+3_000_050_000)
    work={'command':'WORK 3 1000000000\n','send_qpc':base+100_000,'recv_qpc':base+2_999_999_999,
        'response':{'schema':'fixed-work-clock-endpoint-v1','op':'WORK','pid':100,'seq':3,'path':'libc',
                    'selected_cpu':-1,'executed_updates':1_000_000_000,'work_checksum':123}}
    return {'schema':'fixed-work-clock-interval-v1','planned':plan,'qpc_frequency':freq,'start':start,'work':work,'end':end}


class FixedWorkClockTests(unittest.TestCase):
    def checked(self,row): return check_interval(row,1_000_000_000,schedule(17)[0],100,2,list(range(32)))

    def test_schedule_exact_interleaved(self):
        rows=schedule(17)
        self.assertEqual(len(rows),22)
        self.assertEqual([r['index'] for r in rows if r['long']],[8,21])
        self.assertEqual([r['condition'] for r in rows[:8]],['LU','SU','LP','SP','SP','LP','SU','LU'])
        for condition in ('LU','SU','LP','SP'):
            self.assertEqual(sum(r['condition']==condition for r in rows),5)
        self.assertEqual(sum(r['updates'] for r in rows),40_000_000_000)

    def test_valid_integer_precision_and_unpadded(self):
        c=self.checked(fixture()); self.assertTrue(c['raw_pass']); self.assertTrue(c['within_host_unpadded']['raw'])
        self.assertEqual(c['guest_ranges_ns']['raw'],[2_999_999_900,3_000_000_100])

    def test_real_raw_mismatch_rejected(self):
        row=fixture()
        row['end']['response']['raw1_ns']+=100_000_000; row['end']['response']['raw2_ns']+=100_000_000
        c=self.checked(row); self.assertTrue(c['evidence_integrity_pass']); self.assertFalse(c['raw_pass'])

    def test_mono_warning_is_not_raw_proof_or_gate(self):
        row=fixture()
        for key in ('m1_ns','monotonic_ns','m2_ns'): row['end']['response'][key]+=100_000_000
        c=self.checked(row); self.assertTrue(c['raw_pass']); self.assertFalse(c['within_host_with_allowance']['monotonic'])
        row['end']['response']['raw2_ns']+=100_000_000
        self.assertFalse(self.checked(row)['raw_pass'])

    def test_wide_host_boundary_is_indeterminate(self):
        row=fixture(); row['end']['recv_qpc']+=21_000_000
        c=self.checked(row); self.assertFalse(c['reference_determinate']); self.assertFalse(c['raw_pass'])

    def test_wide_raw_read_span_is_indeterminate(self):
        row=fixture(); row['end']['response']['raw2_ns']+=21_000_000
        self.assertFalse(self.checked(row)['reference_determinate'])

    def test_rollbacks_rejected(self):
        row=fixture(); row['start']['response']['raw2_ns']=row['start']['response']['raw1_ns']-1
        self.assertFalse(self.checked(row)['raw_pass'])
        row=fixture(); row['end']['response']['raw1_ns']=row['start']['response']['raw2_ns']
        self.assertFalse(self.checked(row)['raw_pass'])

    def test_sequence_pid_and_work_count(self):
        for field,value in (('seq',8),('pid',101),('executed_updates',999)):
            row=fixture(); row['work']['response'][field]=value
            self.assertFalse(self.checked(row)['evidence_integrity_pass'])

    def test_missing_nonfinite_float_and_boolean_endpoint(self):
        for value in (float('nan'),float('inf'),True,123.0,0,-1):
            row=fixture(); row['start']['response']['raw1_ns']=value
            self.assertFalse(self.checked(row)['raw_pass'])
        row=fixture(); del row['start']['response']['raw1_ns']
        self.assertFalse(self.checked(row)['raw_pass'])

    def test_adjtimex_read_only(self):
        row=fixture(); row['start']['response']['adjtimex']['modes']=1
        self.assertFalse(self.checked(row)['raw_pass'])

    def test_conservative_entire_range_required(self):
        row=fixture(); row['end']['response']['raw1_ns']+=35_000_000
        row['end']['response']['raw2_ns']+=36_000_000
        self.assertFalse(self.checked(row)['raw_pass'])

    def test_old_rule_still_rejects_saved_failure(self):
        from pathlib import Path
        from scripts.p3_clock_reference import audit_diagnostic
        # Existing frozen checker still judges MONOTONIC, not this new RAW decision.
        result=audit_diagnostic(Path(__file__).resolve().parents[1]/'evidence/p3_clock_reference/20261010-190645-1375f246')
        self.assertTrue(result['evidence_integrity_pass'])
        self.assertFalse(result['diagnostic_certifiable'])


if __name__=='__main__': unittest.main()
