"""Bounded read-only WSL metadata; unavailable fields are unknown, not gates."""
import json
import re
import subprocess
import time

commands=[['uname','-a'],['cat','/sys/devices/system/clocksource/clocksource0/current_clocksource'],
    ['cat','/sys/devices/system/clocksource/clocksource0/available_clocksource'],['cat','/proc/uptime'],
    ['cat','/proc/sys/kernel/random/boot_id'],['lscpu'],['timedatectl','status'],
    ['timedatectl','show','-p','NTPSynchronized','-p','NTP','-p','CanNTP'],
    ['systemctl','status','systemd-timesyncd','chrony','ntp','--no-pager'],
    ['journalctl','-u','systemd-timesyncd','-n','30','--no-pager'],['dmesg','--color=never']]
results=[]
for command in commands:
    start=time.monotonic()
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=3,check=False)
        stdout=result.stdout
        if command[0]=='dmesg':
            stdout='\n'.join(line for line in stdout.splitlines() if re.search('tsc|clocksource|timekeep|clock.*unstable',line,re.I))
        results.append({'command':command,'returncode':result.returncode,'stdout':stdout,'stderr':result.stderr,
            'status':'observed' if result.returncode==0 else 'unknown','elapsed_seconds':time.monotonic()-start,
            'stdout_filter':'tsc|clocksource|timekeep|clock.*unstable' if command[0]=='dmesg' else None})
    except (OSError,subprocess.TimeoutExpired) as error:
        results.append({'command':command,'returncode':'unknown','status':'unknown','error':str(error),
                        'elapsed_seconds':time.monotonic()-start})
    print(json.dumps({'schema':'clock-reference-readonly-command-v1',**results[-1]}),flush=True)
