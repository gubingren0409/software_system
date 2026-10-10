"""Versioned RAW candidate contract shared by execution, entry and independent audit."""
from __future__ import annotations
import hashlib,json,math,time
from pathlib import Path

RAW_RESULT_SCHEMA='matrix-multiplication-result-v2'
RAW_VERSION='2026-10-10-raw-candidate-v1'


def protocol_hash(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def load_timing_binding(binding,base):
    if binding is None: return None # Explicit legacy MONOTONIC records.
    if not isinstance(binding,dict) or set(binding)!={'file','hash'}:
        raise ValueError('Invalid timing protocol binding')
    data=json.loads((Path(base)/binding['file']).read_text(encoding='utf-8'))
    if protocol_hash(data)!=binding['hash'] or data.get('schema')!='matrix-raw-timing-protocol-v1' or \
            data.get('version')!=RAW_VERSION or data.get('primary_clock')!='CLOCK_MONOTONIC_RAW' or \
            data.get('result_schema')!=RAW_RESULT_SCHEMA:
        raise ValueError('Timing protocol identity differs')
    expected={'maximum_uncertainty_ns':20_000_000,'maximum_read_span_ns':20_000_000,
              'absolute_allowance_ns':5_000_000,'relative_allowance_percent':1,
              'all_intervals_required':True,'raw_monotonic_equality_required':False,
              'formal_recovery_enabled':False}
    if any(type(data['admission'].get(k)) is not type(v) or data['admission'][k]!=v for k,v in expected.items()):
        raise ValueError('Unsupported RAW candidate admission policy')
    return data


def measurement_timing(protocol,root):
    return load_timing_binding(protocol.get('timing_protocol'),root)


def require_formal_activation(protocol,root):
    timing=measurement_timing(protocol,root)
    if timing is not None and not timing['admission']['formal_recovery_enabled']:
        raise ValueError('RAW candidate only: recovery/Formal/Grid/search are disabled pending external audit and a new matching session/Grid')
    return timing


def check_raw_result(result):
    """No MONOTONIC/RAW equality gate. Aux endpoints are evidence, not a reference."""
    if result.get('primary_clock')!='CLOCK_MONOTONIC_RAW' or result.get('timing_protocol_version')!=RAW_VERSION:
        raise ValueError('Wrong primary clock/timing version')
    for field in ('raw_start_ns','raw_end_ns','monotonic_start_ns','monotonic_end_ns'):
        if type(result.get(field)) is not int or not 0<result[field]<=2**63-1:
            raise ValueError('Invalid integer clock endpoint: '+field)
    delta=result['raw_end_ns']-result['raw_start_ns']
    if delta<=0: raise ValueError('Nonpositive/backward RAW duration')
    seconds=float(delta)/1_000_000_000.0
    mono=float(result['monotonic_end_ns']-result['monotonic_start_ns'])/1_000_000_000.0
    derived={'elapsed_seconds':seconds,'monotonic_elapsed_seconds':mono,
             'monotonic_minus_raw_seconds':mono-seconds}
    for field,value in derived.items():
        actual=result.get(field)
        if type(actual) not in (int,float) or not math.isfinite(actual) or actual!=value:
            raise ValueError('Saved clock delta differs from integer endpoints: '+field)


def execution_clock(raw_candidate):
    # Guest watchdog/cost is explicitly RAW; the enclosing Windows budget remains QPC.
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)/1e9 if raw_candidate else time.monotonic()
