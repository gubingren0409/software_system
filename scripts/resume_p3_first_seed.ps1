param([Parameter(Mandatory=$true)][string]$EvidenceDirectory)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$output = [IO.Path]::GetFullPath($EvidenceDirectory)
$content = 'e308bfb873e6811c50ad685a979af345302fda8d'
$archive = '/var/tmp/matrix-autotuner-p2-content-' + $content
$campaign = Join-Path $repoRoot 'evidence/p3/campaign-e308bfb'
$identity = Join-Path $repoRoot 'evidence/p3/content-e308bfb/git_identity.json'
$criteriaPath = Join-Path $repoRoot 'configs/timing_audit_protocol.json'
$criteria = (Get-Content -LiteralPath $criteriaPath -Raw | ConvertFrom-Json).diagnostic_criteria
if (-not (Test-Path -LiteralPath $output)) { New-Item -ItemType Directory -Path $output | Out-Null }
if (Test-Path -LiteralPath (Join-Path $output 'controller.json')) { throw 'Use a new batch evidence directory' }
$outputWsl = (wsl.exe -d Ubuntu-24.04 -- wslpath -u $output.Replace('\','/')).Trim()
$campaignWsl = (wsl.exe -d Ubuntu-24.04 -- wslpath -u $campaign.Replace('\','/')).Trim()
$identityWsl = (wsl.exe -d Ubuntu-24.04 -- wslpath -u $identity.Replace('\','/')).Trim()

function Write-Record([string]$Name, $Value) {
    [IO.File]::WriteAllText((Join-Path $output $Name), ($Value | ConvertTo-Json -Depth 20) + "`n", [Text.UTF8Encoding]::new($false))
}
function Start-Captured([string]$Name, [string[]]$Arguments) {
    foreach ($argument in $Arguments) { if ($argument -match '[\s"]') { throw 'Arguments must contain no whitespace/quotes' } }
    $start = [DateTime]::UtcNow
    $qpcStart = [Diagnostics.Stopwatch]::GetTimestamp()
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $child = Start-Process -FilePath 'wsl.exe' -ArgumentList $Arguments -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $output ($Name + '.stdout.txt')) `
        -RedirectStandardError (Join-Path $output ($Name + '.stderr.txt'))
    $null = $child.Handle
    while (-not $child.WaitForExit(1000)) { }
    $child.Refresh()
    $timer.Stop()
    $qpcEnd = [Diagnostics.Stopwatch]::GetTimestamp()
    $end = [DateTime]::UtcNow
    if ($null -eq $child.ExitCode) { throw 'Unknown native returncode' }
    $record = [ordered]@{command=@('wsl.exe') + $Arguments; pid=$child.Id; returncode=$child.ExitCode;
        start_utc=$start.ToString('o'); end_utc=$end.ToString('o'); qpc_start=[string]$qpcStart;
        qpc_end=[string]$qpcEnd; qpc_frequency=[string][Diagnostics.Stopwatch]::Frequency;
        utc_seconds=($end-$start).TotalSeconds; stopwatch_seconds=$timer.Elapsed.TotalSeconds;
        stdout_path=$Name+'.stdout.txt'; stderr_path=$Name+'.stderr.txt';
        stdout_sha256=(Get-FileHash -LiteralPath (Join-Path $output ($Name+'.stdout.txt')) -Algorithm SHA256).Hash.ToLower();
        stderr_sha256=(Get-FileHash -LiteralPath (Join-Path $output ($Name+'.stderr.txt')) -Algorithm SHA256).Hash.ToLower()}
    Write-Record ($Name + '.operation.json') $record
    return $record
}
function Check-Clocks([string]$Name) {
    $record = Start-Captured $Name @('-d','Ubuntu-24.04','--cd',$archive,'--','env','-u','PYTHONPATH',
        'PYTHONDONTWRITEBYTECODE=1','python3','scripts/check_p2_clocks.py','--intervals','3','--seconds','3',
        '--skip-host','--output',($outputWsl+'/'+$Name+'.wsl.json'))
    if ($record.returncode -ne 0) { throw ('Clock probe failed: ' + $Name) }
    $probe = Get-Content -LiteralPath (Join-Path $output ($Name+'.wsl.json')) -Raw | ConvertFrom-Json
    $checks = @($probe.wsl_intervals | ForEach-Object {
        $delta = $_.delta
        [ordered]@{monotonic_raw_pass=([Math]::Abs($delta.monotonic_seconds-$delta.raw_seconds) -le $criteria.monotonic_raw_absolute_allowance_seconds+$criteria.monotonic_raw_relative_tolerance*$delta.raw_seconds);
            realtime_raw_pass=([Math]::Abs($delta.realtime_seconds-$delta.raw_seconds) -le $criteria.realtime_raw_absolute_allowance_seconds+$criteria.realtime_raw_relative_tolerance*$delta.raw_seconds);
            delta=$delta}
    })
    $hostPass = [Math]::Abs($record.utc_seconds-$record.stopwatch_seconds) -le $criteria.realtime_raw_absolute_allowance_seconds+$criteria.realtime_raw_relative_tolerance*$record.stopwatch_seconds
    $pass = $hostPass -and @($checks | Where-Object { -not $_.monotonic_raw_pass -or -not $_.realtime_raw_pass }).Count -eq 0
    Write-Record ($Name+'.check.json') ([ordered]@{pass=$pass; wsl_intervals=$checks; probe_script_sha256=$probe.script_sha256;
        host_utc_stopwatch_pass=$hostPass; criteria_source='configs/timing_audit_protocol.json';
        scope='WSL same-interval sleep clocks; Windows same-interval whole invocation UTC/QPC. Host invocation is not compared with the sum of WSL sleeps.';
        calibration_applied=$false; performance_protocol_modified=$false})
    return $pass
}

$baseline = Get-Content -LiteralPath (Join-Path $campaign 'checkpoint.json') -Raw | ConvertFrom-Json
$state = [ordered]@{schema='p3-first-seed-controller-v1'; status='created'; audit_baseline='e46b96cff35e7ea3b23c0b1eaef5fc66b03399ec';
    content_commit=$content; campaign_directory=$campaign; archive_root=$archive; trajectory_limit=2;
    controller_commit=(git -C $repoRoot rev-parse HEAD).Trim(); controller_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower();
    clock_criteria_sha256=(Get-FileHash -LiteralPath $criteriaPath -Algorithm SHA256).Hash.ToLower();
    original_session_id=$baseline.session_id; initial_active_seconds=$baseline.active_total_seconds;
    initial_wait_seconds=$baseline.wait_seconds; started_utc=[DateTimeOffset]::UtcNow.ToString('o')}
Write-Record 'campaign_checkpoint_before.json' $baseline
Write-Record 'trajectory_checkpoint_before.json' (Get-Content -LiteralPath (Join-Path $campaign 'trajectories/00_random_20261008/checkpoint.json') -Raw | ConvertFrom-Json)
$sampleFile = Join-Path $campaign 'trajectories/00_random_20261008/samples.jsonl'
Write-Record 'samples_prefix_before.json' ([ordered]@{path=$sampleFile; bytes=(Get-Item -LiteralPath $sampleFile).Length;
    sha256=(Get-FileHash -LiteralPath $sampleFile -Algorithm SHA256).Hash.ToLower()})
$timer = [Diagnostics.Stopwatch]::StartNew()
try {
    Write-Record 'controller.json' $state
    if (-not (Check-Clocks 'clock_before')) { $state.status='clock_rejected_before'; throw 'Pre-batch clock checks failed; campaign not resumed' }
    $state.status='running'
    Write-Record 'controller.json' $state
    $operation = Start-Captured 'campaign' @('-d','Ubuntu-24.04','--cd',$archive,'--','env','-u','PYTHONPATH',
        'PYTHONDONTWRITEBYTECODE=1','python3','-m','autotuner','campaign','--content-sha',$content,
        '--git-identity',$identityWsl,'--campaign-directory',$campaignWsl,'--trajectory-limit','2','--resume')
    $state.campaign_returncode=$operation.returncode
    $state.status=if ($operation.returncode -eq 0) { 'batch_returned' } else { 'campaign_paused_or_failed' }
} catch {
    $state.failure=$_.Exception.Message
    if ($state.status -eq 'running') { $state.status='controller_failure' }
} finally {
    try {
        $state.after_clock_pass=Check-Clocks 'clock_after'
        if (-not $state.after_clock_pass) { $state.status='clock_warning_after' }
    } catch { $state.after_clock_error=$_.Exception.Message; $state.status='clock_check_failure_after' }
    $current = Get-Content -LiteralPath (Join-Path $campaign 'checkpoint.json') -Raw | ConvertFrom-Json
    Write-Record 'campaign_checkpoint_after.json' $current
    $state.final_campaign_status=$current.status
    $state.completed_trajectory_count=@($current.completed_trajectories).Count
    $state.campaign_active_delta_seconds=$current.active_total_seconds-$baseline.active_total_seconds
    $state.campaign_wait_delta_seconds=$current.wait_seconds-$baseline.wait_seconds
    $state.host_controller_seconds=$timer.Elapsed.TotalSeconds
    $state.ended_utc=[DateTimeOffset]::UtcNow.ToString('o')
    Write-Record 'controller.json' $state
    $state | ConvertTo-Json -Depth 6
}
if ($state.status -ne 'batch_returned' -or $state.final_campaign_status -ne 'batch_complete' -or $state.completed_trajectory_count -ne 2) { exit 2 }
