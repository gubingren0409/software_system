"""Copy, do not move/delete, the failed activity to an emergency C: workspace."""
import ctypes
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path('E:/software_system/project01/evidence/p3_raw_comparison/20261014-182807-ac-validation')
TARGET = ROOT / 'activity-backup'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def disks():
    result = {}
    for name in ('C:/', 'E:/'):
        usage = shutil.disk_usage(name)
        result[name] = {'total_bytes': usage.total, 'used_bytes': usage.used, 'free_bytes': usage.free}
    return result


def main():
    if TARGET.exists(): raise ValueError('Never replace a rescue copy')
    before = {path.relative_to(SOURCE).as_posix(): {'sha256': digest(path), 'bytes': path.stat().st_size}
              for path in SOURCE.rglob('*') if path.is_file()}
    available = disks()
    shutil.copytree(SOURCE, TARGET)
    after = {path.relative_to(TARGET).as_posix(): {'sha256': digest(path), 'bytes': path.stat().st_size}
             for path in TARGET.rglob('*') if path.is_file()}
    if before != after: raise ValueError('Rescue bytes differ')
    value = {'at': datetime.now().astimezone().isoformat(), 'source': str(SOURCE), 'rescue_copy': str(TARGET),
             'method': 'Verified copy only; no source moves/deletes/edits', 'disk_state': available,
             'copied_files': len(before), 'copied_bytes': sum(v['bytes'] for v in before.values()),
             'all_file_bytes_verified': True, 'files': before}
    (ROOT / 'rescue_manifest.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in value.items() if k!='files'}),flush=True)


if __name__ == '__main__': main()
