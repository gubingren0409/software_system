"""Temporary Windows controller-thread sleep request and immutable power event reads."""
from __future__ import annotations

import ctypes
import json
import os
import threading
from pathlib import Path

from scripts.p3_clock_contract import POWERSHELL, atomic_write_json, capture, load

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
STANDBY_IDS = {42, 506}


class SleepRequest:
    def __init__(self, path, function=None):
        self.path = Path(path)
        if function is None:
            if os.name != 'nt': raise ValueError('Windows sleep request required')
            function = ctypes.WinDLL('kernel32', use_last_error=True).SetThreadExecutionState
            function.argtypes = [ctypes.c_uint32]; function.restype = ctypes.c_uint32
        self.function = function
        self.record = {'schema': 'raw-comparison-sleep-request-v1', 'thread_id': threading.get_ident(),
            'request_flags': ES_CONTINUOUS | ES_SYSTEM_REQUIRED, 'release_flags': ES_CONTINUOUS,
            'acquired': False, 'released': False, 'limitation': 'Does not guarantee prevention of user lid closure'}

    def __enter__(self):
        result = int(self.function(self.record['request_flags']))
        self.record.update(acquire_result=result, acquired=result != 0)
        atomic_write_json(self.path, self.record)
        if not result: raise OSError('SetThreadExecutionState request failed')
        return self

    def __exit__(self, kind, error, traceback):
        result = int(self.function(ES_CONTINUOUS))
        self.record.update(release_result=result, released=result != 0,
            release_thread_id=threading.get_ident(), exception=None if error is None else str(error))
        atomic_write_json(self.path, self.record)
        if not result: raise OSError('SetThreadExecutionState release failed')
        return False


class PowerEvents:
    def __init__(self, directory, timeout=20):
        self.directory = Path(directory); self.timeout = timeout; self.cursor = None; self.count = 0
        self.boot = None

    def read(self):
        cursor = -1 if self.cursor is None else self.cursor
        # First bound the record range; a later poll captures events beyond upper.
        script = """
$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$top=Get-WinEvent -LogName System -MaxEvents 1
$os=Get-CimInstance Win32_OperatingSystem
$events=@()
if (CURSOR -ge 0) {
  $xpath="*[System[(EventRecordID > CURSOR and EventRecordID <= $($top.RecordId)) and ((Provider[@Name='Microsoft-Windows-Kernel-Power'] and (EventID=42 or EventID=506 or EventID=107 or EventID=507)) or (Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1))]]"
  $events=@(Get-WinEvent -LogName System -FilterXPath $xpath -ErrorAction SilentlyContinue | Sort-Object RecordId | ForEach-Object {
    [ordered]@{record_id=[int64]$_.RecordId;event_id=$_.Id;provider=$_.ProviderName;time_utc=$_.TimeCreated.ToUniversalTime().ToString('o');message=$_.Message;xml=$_.ToXml()}
  })
  if ($Error.Count -gt 0 -and $Error[0].FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*') { throw $Error[0] }
}
[ordered]@{schema='raw-comparison-power-events-v1';log='System';cursor_before=CURSOR;cursor_after=[int64]$top.RecordId;windows_boot_utc=$os.LastBootUpTime.ToUniversalTime().ToString('o');events=$events;at=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json -Depth 8
""".replace('CURSOR', str(cursor))
        name = 'events_' + str(self.count); self.count += 1
        operation = capture([POWERSHELL, '-NoProfile', '-Command', script], self.directory, name,
                            'raw-comparison-power-events', timeout=self.timeout)
        if operation['returncode'] != 0 or operation['timed_out']:
            raise ValueError('Power event query failed; continuity unknown')
        record = load(self.directory / operation['stdout_path'])
        validate_event_record(record, cursor, self.boot)
        self.boot = record['windows_boot_utc']; self.cursor = record['cursor_after']
        return {'operation_name': name, 'record': record}


def validate_event_record(record, cursor, boot=None):
    if record['schema'] != 'raw-comparison-power-events-v1' or record['log'] != 'System' or \
            type(record['cursor_after']) is not int or record['cursor_after'] < max(0, cursor) or \
            record['cursor_before'] != cursor or not isinstance(record['events'], list) or \
            not record['windows_boot_utc'] or (boot is not None and boot != record['windows_boot_utc']):
        raise ValueError('Power event log reset or identity invalid')
    previous = cursor
    for event in record['events']:
        if type(event['record_id']) is not int or not previous < event['record_id'] <= record['cursor_after'] or \
                type(event['event_id']) is not int or event['event_id'] not in (1, 42, 107, 506, 507) or \
                event['provider'] not in ('Microsoft-Windows-Kernel-Power', 'Microsoft-Windows-Power-Troubleshooter') or \
                not all(isinstance(event[key], str) and event[key] for key in ('message', 'xml', 'time_utc')):
            raise ValueError('Power event original message/sequence missing')
        previous = event['record_id']


def standby_events(records):
    return [event for record in records for event in record['events']
            if event['provider'] == 'Microsoft-Windows-Kernel-Power' and event['event_id'] in STANDBY_IDS]
