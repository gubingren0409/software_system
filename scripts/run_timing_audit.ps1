param(
    [Parameter(Mandatory=$true)][string]$ContentSha,
    [Parameter(Mandatory=$true)][string]$ArchiveRoot,
    [Parameter(Mandatory=$true)][string]$GitIdentity,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($ContentSha -notmatch '^[0-9a-f]{40}$') { throw 'Expected full content SHA' }
$auditOutput = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $auditOutput) { throw 'Diagnostic output must be a new directory' }
New-Item -ItemType Directory -Path $auditOutput | Out-Null
$auditOutputWsl = (wsl.exe -d Ubuntu-24.04 -- wslpath -u $auditOutput.Replace('\','/')).Trim()
$identityWsl = (wsl.exe -d Ubuntu-24.04 -- wslpath -u $GitIdentity.Replace('\','/')).Trim()
$resourceScript = (wsl.exe -d Ubuntu-24.04 -- wslpath -w ($ArchiveRoot + '/scripts/check_p2_resources.ps1')).Trim()
$protocol = Get-Content (Join-Path $PSScriptRoot '../configs/timing_audit_protocol.json') -Raw | ConvertFrom-Json
$measurement = Get-Content (Join-Path $PSScriptRoot '../configs/measurement_protocol.json') -Raw | ConvertFrom-Json
$checkpoint = [ordered]@{schema='timing-audit-host-v1'; content_commit=$ContentSha; status='created'; completed_groups=@(); gate_wait_seconds=0.0}

function Write-AuditJson([string]$Path, $Value) {
    New-Item -ItemType Directory -Force ([IO.Path]::GetDirectoryName($Path)) | Out-Null
    $temporary = $Path + '.tmp'
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 15) + "`n", [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}
function Save-Checkpoint { Write-AuditJson (Join-Path $auditOutput 'checkpoint.json') $checkpoint }
function Invoke-Captured([string]$Name, [string]$Executable, [string[]]$Arguments, [int]$TimeoutSeconds) {
    foreach ($argument in $Arguments) { if ($argument -match '[\s"]') { throw 'Diagnostic arguments must contain no whitespace/quotes' } }
    $directory = Join-Path $auditOutput 'host_operations'
    New-Item -ItemType Directory -Force $directory | Out-Null
    $stdoutFile = Join-Path $directory ($Name + '.stdout.txt')
    $stderrFile = Join-Path $directory ($Name + '.stderr.txt')
    $startUtc = [DateTime]::UtcNow
    $startQpc = [Diagnostics.Stopwatch]::GetTimestamp()
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile -PassThru
    $null = $process.Handle
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        throw ('Own diagnostic operation exceeded watchdog; inspect preserved process/logs before any retry: ' + $Name)
    }
    $process.Refresh()
    if ($null -eq $process.ExitCode) { throw ('Unknown native returncode: ' + $Name) }
    $timer.Stop()
    $endQpc = [Diagnostics.Stopwatch]::GetTimestamp()
    $endUtc = [DateTime]::UtcNow
    $record = [ordered]@{id=$Name; executable=$Executable; arguments=$Arguments; pid=$process.Id;
        returncode=$process.ExitCode; stdout=[IO.File]::ReadAllText($stdoutFile); stderr=[IO.File]::ReadAllText($stderrFile);
        qpc_frequency=[string][Diagnostics.Stopwatch]::Frequency; start_qpc=[string]$startQpc; end_qpc=[string]$endQpc;
        start_utc=$startUtc.ToString('o'); end_utc=$endUtc.ToString('o'); start_utc_ticks=[string]$startUtc.Ticks;
        end_utc_ticks=[string]$endUtc.Ticks; stopwatch_seconds=$timer.Elapsed.TotalSeconds;
        utc_seconds=($endUtc-$startUtc).TotalSeconds; scope='whole child invocation including startup and output'}
    Write-AuditJson (Join-Path $directory ($Name + '.json')) $record
    return $record
}
function Number-InRange($Value, [double]$Minimum, [double]$Maximum) {
    return (($Value -is [int] -or $Value -is [long] -or $Value -is [double] -or $Value -is [decimal]) -and
        -not [double]::IsNaN([double]$Value) -and -not [double]::IsInfinity([double]$Value) -and
        $Value -ge $Minimum -and $Value -le $Maximum)
}
function Formal-Gate([string]$Purpose) {
    $gateTimer = [Diagnostics.Stopwatch]::StartNew()
    for ($retry=0; $retry -lt 16; $retry++) {
        $name = 'gate_' + $Purpose + '_' + $retry
        $record = Invoke-Captured $name 'powershell.exe' @('-NoProfile','-File',$resourceScript,'-Mode','Formal') 60
        $pass = $false
        try {
            $parsed = $record.stdout.TrimStart([char]0xfeff) | ConvertFrom-Json
            $limits = $measurement.resource_gate
            $pass = ($record.returncode -eq 0 -and $parsed.schema -eq 'p2-resource-gate-v2' -and
                $parsed.mode -eq 'Formal' -and $parsed.formal_gate -eq 'PASS' -and
                (Number-InRange $parsed.host_minimum_available_bytes $limits.formal_host_minimum_available_bytes ([double]::MaxValue)) -and
                (Number-InRange $parsed.wsl_available_bytes $limits.formal_wsl_minimum_available_bytes ([double]::MaxValue)) -and
                (Number-InRange $parsed.wsl_root_free_bytes $limits.formal_wsl_root_minimum_free_bytes ([double]::MaxValue)) -and
                (Number-InRange $parsed.host_cpu_average_percent 0 $limits.formal_host_cpu_average_maximum_percent) -and
                (Number-InRange $parsed.host_cpu_maximum_percent 0 $limits.formal_host_cpu_single_sample_maximum_percent))
        } catch { $pass = $false }
        if ($pass) {
            $checkpoint.gate_wait_seconds += $gateTimer.Elapsed.TotalSeconds
            Save-Checkpoint
            return
        }
        $checkpoint.status = 'resource_paused'
        Save-Checkpoint
        Write-Output ('resource_paused: ' + $Purpose + ' attempt ' + $retry)
        if ($retry -lt 15) { Start-Sleep -Seconds 30 }
    }
    $checkpoint.gate_wait_seconds += $gateTimer.Elapsed.TotalSeconds
    Save-Checkpoint
    throw ('Resource gate did not recover: ' + $Purpose)
}
function Invoke-Python([string]$Name, [string[]]$Tail, [int]$TimeoutSeconds) {
    $arguments = @('-d','Ubuntu-24.04','--cd',$ArchiveRoot,'--','env','-u','PYTHONPATH',
        'PYTHONDONTWRITEBYTECODE=1','timeout','--kill-after=30',([string]($TimeoutSeconds-30)),
        'python3','scripts/timing_audit.py','--output',$auditOutputWsl,'--content-sha',$ContentSha) + $Tail
    $record = Invoke-Captured $Name 'wsl.exe' $arguments $TimeoutSeconds
    if ($record.returncode -ne 0) { throw ('Diagnostic operation failed: ' + $Name + '; see retained stdout/stderr') }
    return $record
}

$totalTimer = [Diagnostics.Stopwatch]::StartNew()
try {
    Save-Checkpoint
    Formal-Gate 'setup'
    Invoke-Python 'setup' @('--action','setup','--git-identity',$identityWsl) 900 | Out-Null
    for ($i=0; $i -lt $protocol.clock_probes.before_count; $i++) {
        Invoke-Python ('before'+$i) @('--action','probe','--probe-id',('before'+$i)) 90 | Out-Null
    }
    for ($i=0; $i -lt $protocol.groups.Count; $i++) {
        $job = $protocol.groups[$i]
        Formal-Gate $job.id
        $checkpoint.status = 'measuring'
        $checkpoint.active_group = $job.id
        Save-Checkpoint
        Write-Output ('group_start: ' + $job.id)
        $timeout = 6 * [int]$measurement.formal_timeout_seconds.($job.optimization) + 180
        Invoke-Python $job.id @('--action','group','--group-index',([string]$i)) $timeout | Out-Null
        $checkpoint.completed_groups += $job.id
        $checkpoint.active_group = $null
        Save-Checkpoint
        Write-Output ('group_complete: ' + $job.id)
    }
    for ($i=0; $i -lt $protocol.clock_probes.after_count; $i++) {
        Invoke-Python ('after'+$i) @('--action','probe','--probe-id',('after'+$i)) 90 | Out-Null
    }
    Invoke-Python 'analyze' @('--action','analyze') 120 | Out-Null
    $checkpoint.status = 'complete'
} catch {
    if ($checkpoint.status -ne 'resource_paused') { $checkpoint.status = 'diagnostic_failure' }
    $checkpoint.failure = $_.Exception.Message
    throw
} finally {
    $checkpoint.host_total_seconds = $totalTimer.Elapsed.TotalSeconds
    Save-Checkpoint
}
