param([string]$OutputPath = 'evidence/p2/environment/host_clock_bridge_20261008.json')
$ErrorActionPreference = 'Stop'
$arguments = '-d Ubuntu-24.04 --cd /mnt/e/software_system/project01 -- env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_p2_clocks.py --intervals 10 --seconds 3 --skip-host --output evidence/p2/environment/clock_probe_long_20261008.json'
$info = [Diagnostics.ProcessStartInfo]::new('wsl.exe', $arguments)
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
$info.RedirectStandardOutput = $true
$info.RedirectStandardError = $true
$process = [Diagnostics.Process]::new()
$process.StartInfo = $info
$before = [DateTimeOffset]::UtcNow
$timer = [Diagnostics.Stopwatch]::StartNew()
[void]$process.Start()
$outTask = $process.StandardOutput.ReadToEndAsync()
$errTask = $process.StandardError.ReadToEndAsync()
if (-not $process.WaitForExit(50000)) { throw 'Clock probe timeout; no system settings changed' }
$timer.Stop()
$after = [DateTimeOffset]::UtcNow
$record = [ordered]@{
    schema = 'p2-host-clock-bridge-v1'
    collector_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    command = @('wsl.exe', $arguments)
    before_utc = $before.ToString('o')
    after_utc = $after.ToString('o')
    windows_utc_seconds = ($after - $before).TotalSeconds
    windows_stopwatch_seconds = $timer.Elapsed.TotalSeconds
    stdout = $outTask.Result
    stderr = $errTask.Result
    returncode = $process.ExitCode
    system_settings_modified = $false
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath), ($record | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
[pscustomobject]@{returncode=$record.returncode;windows_utc_seconds=$record.windows_utc_seconds;windows_stopwatch_seconds=$record.windows_stopwatch_seconds;output=$OutputPath} | ConvertTo-Json -Compress
