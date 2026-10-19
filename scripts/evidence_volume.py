"""Evidence-volume admission only; no matrix, search, or system-memory changes."""
from pathlib import Path

from autotuner.core import sha256_file, utc_now
from scripts.p3_clock_contract import atomic_write_json, load
from scripts.raw_clock_contract import local_path
from scripts.resume_raw_validation import evidence_preflight


def check_volume(directory, record_path, context):
    directory = Path(directory).resolve()
    record = {'schema': 'evidence-volume-check-v1', 'directory': str(directory),
        'context': context, 'at': utc_now(), 'minimum_free_bytes': 1024**3, 'passed': False}
    try:
        # Reuse the already tested disk_usage + actual write/fsync/read-back helper.
        record.update(evidence_preflight(directory))
        record['passed'] = True
    except (ValueError, OSError) as error:
        record.update(error_type=type(error).__name__, error=str(error), errno=getattr(error, 'errno', None))
        atomic_write_json(record_path, record)
        raise
    atomic_write_json(record_path, record)
    return record


def audit_volume(record_path, directory, context):
    record = load(record_path); directory = local_path(directory).resolve()
    if record['schema'] != 'evidence-volume-check-v1' or record['context'] != context or \
            local_path(record['directory']).resolve() != directory or record['passed'] is not True or \
            type(record['free_bytes']) is not int or type(record['minimum_free_bytes']) is not int or \
            record['minimum_free_bytes'] != 1024**3 or record['free_bytes'] < 1024**3:
        raise ValueError('Evidence volume admission identity/free space differs')
    probe = local_path(record['write_probe']).resolve()
    if not probe.is_relative_to(directory) or sha256_file(probe) != record['sha256'] or \
            probe.read_bytes() != b'owned evidence-volume write/fsync/read-back probe\n':
        raise ValueError('Evidence volume write/fsync/read-back evidence differs')
    return record
