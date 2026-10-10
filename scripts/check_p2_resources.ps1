param(
    [ValidateSet('Formal', 'Recovery', 'Snapshot')][string]$Mode = 'Formal',
    [string]$OutputPath = '',
    [string]$RuntimeRoot = '',
    [string]$InputSnapshot = ''
)
$ErrorActionPreference = 'Stop'
try {
    # This child process only; no system/module/execution-policy setting is changed.
    $env:PSModulePath = 'C:\Windows\System32\WindowsPowerShell\v1.0\Modules'
    if (-not $RuntimeRoot) {
        $RuntimeRoot = (wsl.exe -d Ubuntu-24.04 -- wslpath -u (Split-Path $PSScriptRoot -Parent)).Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Runtime root conversion failed' }
    }
    $policyPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'configs\resource_policy.json'
    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    if ($InputSnapshot) {
        if ($Mode -eq 'Snapshot') { throw 'Snapshot input requires an admission purpose' }
        $rawJson = Get-Content -LiteralPath $InputSnapshot -Raw
        $answer = $rawJson | wsl.exe -d Ubuntu-24.04 --cd $RuntimeRoot -- env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 -m autotuner.resources --policy configs/resource_policy.json --purpose $Mode
        $answerExit = $LASTEXITCODE
        if ($OutputPath) { [IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath), ($answer -join "`n") + "`n", [Text.UTF8Encoding]::new($false)) }
        Write-Output $answer
        exit $answerExit
    }
    $windowStart = [DateTimeOffset]::Now.ToString('o')
    $hostOs = Get-CimInstance Win32_OperatingSystem
    $hostOsCaptured = [DateTimeOffset]::Now.ToString('o')
    $samples = @()
    $sampleCount = $(if ($Mode -eq 'Snapshot') { 1 } else { [int]$policy.sample_count })
    for ($index = 0; $index -lt $sampleCount; $index++) {
        $cpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total'
        $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
        if ($null -eq $cpu -or $null -eq $memory) { throw 'Required host counters unavailable' }
        $samples += [ordered]@{
            timestamp = [DateTimeOffset]::Now.ToString('o')
            cpu_percent = [double]$cpu.PercentProcessorTime
            available_memory_bytes = [int64]$memory.AvailableBytes
            committed_bytes = [int64]$memory.CommittedBytes
            commit_limit_bytes = [int64]$memory.CommitLimit
            percent_committed_bytes_in_use = [double]$memory.PercentCommittedBytesInUse
            pages_per_second = [int64]$memory.PagesPersec
            page_reads_per_second = [int64]$memory.PageReadsPersec
            memory_temperature_or_throttling = 'unknown'
        }
        if ($index + 1 -lt $sampleCount) { Start-Sleep -Seconds $policy.sample_interval_seconds }
    }
    $result = [ordered]@{
        schema = 'p2-resource-gate-v2'
        captured_at_local = [DateTimeOffset]::Now.ToString('o')
        mode = $Mode
        host_total_visible_bytes = [int64]$hostOs.TotalVisibleMemorySize * 1KB
        host_samples = $samples
        host_minimum_available_bytes = [int64](($samples | ForEach-Object { $_.available_memory_bytes } | Measure-Object -Minimum).Minimum)
        host_cpu_average_percent = [double](($samples | ForEach-Object { $_.cpu_percent } | Measure-Object -Average).Average)
        host_cpu_maximum_percent = [double](($samples | ForEach-Object { $_.cpu_percent } | Measure-Object -Maximum).Maximum)
        minimum_memory_bytes = [int64]$policy.host_minimum_available_bytes
        minimum_disk_bytes = [int64]$policy.wsl_root_minimum_free_bytes
        sampling_window_start = $windowStart
        host_os_crosscheck = [ordered]@{captured_at=$hostOsCaptured; available_memory_bytes=[int64]$hostOs.FreePhysicalMemory * 1KB; interface='Win32_OperatingSystem.FreePhysicalMemory'}
    }
    if ($Mode -ne 'Snapshot') {
        $meminfo = wsl.exe -d Ubuntu-24.04 -- cat /proc/meminfo
        if ($LASTEXITCODE -ne 0) { throw 'WSL memory query failed' }
        $wslMemory = @{}
        foreach ($line in $meminfo) {
            if ($line -match '^([A-Za-z_]+):\s+(\d+)\s+kB') { $wslMemory[$matches[1]] = [int64]$matches[2] * 1KB }
        }
        $disk = wsl.exe -d Ubuntu-24.04 -- df -B1 --output=avail /
        if ($LASTEXITCODE -ne 0) { throw 'WSL disk query failed' }
        $result.wsl_available_bytes = [int64]$wslMemory.MemAvailable
        $result.wsl_total_bytes = [int64]$wslMemory.MemTotal
        $result.wsl_swap_total_bytes = [int64]$wslMemory.SwapTotal
        $result.wsl_swap_free_bytes = [int64]$wslMemory.SwapFree
        $result.wsl_root_free_bytes = [int64]($disk[-1].Trim())
        $result.wsl_meminfo = @($meminfo)
        $result.vmmem = 'unknown: no readable VmmemWSL/Vmmem process'
        try {
            $vmProcesses = @(Get-Process -Name VmmemWSL,Vmmem -ErrorAction SilentlyContinue | ForEach-Object {
                [ordered]@{pid=$_.Id; name=$_.ProcessName; working_set_bytes=$_.WorkingSet64; private_bytes=$_.PrivateMemorySize64}
            })
            if ($vmProcesses.Count) { $result.vmmem = $vmProcesses }
        } catch { $result.vmmem = 'unknown: Vmmem query unavailable' }
        $result.sampling_window_end = [DateTimeOffset]::Now.ToString('o')
        $result.schema = 'p3-resource-snapshot-v2'
        $result.collector_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower()
        $collectorText = [IO.File]::ReadAllText($PSCommandPath).Replace("`r`n", "`n")
        $collectorHash = [Security.Cryptography.SHA256]::Create()
        try { $result.collector_lf_sha256 = ([BitConverter]::ToString($collectorHash.ComputeHash([Text.Encoding]::UTF8.GetBytes($collectorText)))).Replace('-', '').ToLower() }
        finally { $collectorHash.Dispose() }
        $rawJson = $result | ConvertTo-Json -Depth 8 -Compress
        # PowerShell and Python deliberately use the SAME decision implementation.
        $answer = $rawJson | wsl.exe -d Ubuntu-24.04 --cd $RuntimeRoot -- env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 -m autotuner.resources --policy configs/resource_policy.json --purpose $Mode
        $answerExit = $LASTEXITCODE
        if ($OutputPath) { [IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath), ($answer -join "`n") + "`n", [Text.UTF8Encoding]::new($false)) }
        Write-Output $answer
        exit $answerExit
    } else { $result.formal_gate = 'NOT_APPLICABLE' }
    $json = $result | ConvertTo-Json -Depth 8 -Compress
    if ($OutputPath) { [IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath), $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false)) }
    Write-Output $json
} catch {
    [ordered]@{schema='p3-resource-gate-v4'; mode=$Mode; purpose=$Mode; decision='ERROR'; formal_gate='ERROR'; recovery_gate='ERROR'; rejection_reasons=@($_.Exception.Message); captured_at_local=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json -Compress
    exit 3
}
