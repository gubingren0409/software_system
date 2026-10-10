"""Read-only small-size RAW contract audit. Never creates a recovery certificate."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autotuner.core import ConfigSpace,TargetAdapter,classify_execution,sha256_file,sha256_json,sha256_text
from autotuner.session import source_identity
from autotuner.timing import RAW_RESULT_SCHEMA,measurement_timing


def audit(result_path,target_path,identity_path):
    record=json.loads(result_path.read_text()); target=TargetAdapter.load(target_path)
    protocol=json.loads((ROOT/'configs/measurement_protocol.json').read_text())
    timing=measurement_timing(protocol,ROOT)
    if timing is None or timing!=target.timing_protocol: raise ValueError('Target/measurement timing differs')
    identity=json.loads(identity_path.read_text()); files=source_identity(ROOT,identity['files'])
    context=record['context']; config=record['config']
    expected={'n':context['matrix_n'],'block_size':config['block_size'],'seed':context['seed'],
        'input':context['input_pattern'],'input_generator':protocol['input_generator'],
        'abs_tol':protocol['abs_tolerance'],'rel_tol':protocol['rel_tolerance'],
        'primary_clock':timing['primary_clock'],'timing_protocol_version':timing['version']}
    classification,parsed,detail=classify_execution(record['returncode'],record['timed_out'],record['raw_stdout'],RAW_RESULT_SCHEMA,expected)
    run=result_path.parent
    if (run/'stdout.txt').read_text()!=record['raw_stdout'] or sha256_text(record['raw_stdout'])!=record['stdout_sha256'] or \
            (run/'stderr.txt').read_text()!=record['raw_stderr'] or sha256_text(record['raw_stderr'])!=record['stderr_sha256']:
        raise ValueError('Raw execution streams differ')
    binary=Path(record['command'][0])
    if sha256_file(binary)!=record['binary_sha256'] or sha256_file(Path(record['command'][-1]))!=record['reference_sha256']:
        raise ValueError('Actual binary/reference differs')
    if classification!='success' or record['classification']!=classification or record['target_result']!=parsed or \
            record['score_seconds']!=parsed['elapsed_seconds'] or record['source']!='fresh_measurement' or \
            context['force_remeasure'] is not True or context['matrix_n']!=17 or \
            record['timing_protocol_hash']!=protocol['timing_protocol']['hash']:
        raise ValueError('Not a valid fresh n=17 RAW candidate result: '+detail)
    space=ConfigSpace.load(ROOT/'configs/config_space.json').all()
    if len(space)!=20 or len(set(space))!=20: raise ValueError('Configuration space differs')
    return {'schema':'raw-candidate-validation-v1','candidate_validation_pass':True,'evidence_integrity_pass':True,
        'content_commit':identity['content_sha'],'source_identity':files,'timing_protocol_hash':protocol['timing_protocol']['hash'],
        'measurement_protocol_hash':sha256_json(protocol),'result_sha256':sha256_file(result_path),
        'checked_entries':parsed['checked_entries'],'primary_clock':parsed['primary_clock'],
        'raw_delta_ns':parsed['raw_end_ns']-parsed['raw_start_ns'],'elapsed_seconds':parsed['elapsed_seconds'],
        'auxiliary_monotonic_minus_raw_seconds':parsed['monotonic_minus_raw_seconds'],
        'unique_configuration_count':20,'execution_complete':False,'timing_checks_pass':False,'comparison_ready':False,
        'recovery_certificate_created':False,'formal_target_execution_count':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result',type=Path,required=True); parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--git-identity',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); result=audit(args.result,args.target,args.git_identity)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))
