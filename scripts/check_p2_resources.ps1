param(
    [ValidateSet('Formal', 'Snapshot')][string]$Mode = 'Formal',
    [string]$OutputPath = ''
)
$ErrorActionPreference = 'Stop'
try {
    $hostOs = Get-CimInstance Win32_OperatingSystem
    $samples = @()
    $sampleCount = $(if ($Mode -eq 'Formal') { 5 } else { 1 })
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
        if ($index + 1 -lt $sampleCount) { Start-Sleep -Seconds 1 }
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
        minimum_memory_bytes = 2GB
        minimum_disk_bytes = 1GB
    }
    if ($Mode -eq 'Formal') {
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
        $pass = $result.host_minimum_available_bytes -ge 2GB -and $result.wsl_available_bytes -ge 2GB -and `
            $result.wsl_root_free_bytes -ge 1GB -and $result.host_cpu_average_percent -le 10 -and `
            $result.host_cpu_maximum_percent -le 20
        $result.formal_gate = $(if ($pass) { 'PASS' } else { 'REJECT' })
    } else { $result.formal_gate = 'NOT_APPLICABLE' }
    $json = $result | ConvertTo-Json -Depth 8 -Compress
    if ($OutputPath) { [IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputPath), $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false)) }
    Write-Output $json
    if ($Mode -eq 'Formal' -and -not $pass) { exit 2 }
} catch {
    [ordered]@{schema='p2-resource-gate-v2'; mode=$Mode; formal_gate='ERROR'; error=$_.Exception.Message; captured_at_local=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json -Compress
    exit 3
}
