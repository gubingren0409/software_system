$ErrorActionPreference = 'Stop'

$hostOs = Get-CimInstance Win32_OperatingSystem
$hostAvailableBytes = [int64]$hostOs.FreePhysicalMemory * 1KB
$cpuSamples = @()
for ($index = 0; $index -lt 5; $index++) {
    $cpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor |
        Where-Object Name -eq '_Total'
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    $cpuSamples += [pscustomobject]@{
        timestamp = [DateTimeOffset]::Now.ToString('o')
        cpu_percent = [double]$cpu.PercentProcessorTime
        available_memory_bytes = [int64]$memory.AvailableBytes
    }
    if ($index -lt 4) {
        Start-Sleep -Seconds 1
    }
}

$wslAvailableKiB = [int64](wsl.exe -d Ubuntu-24.04 -- bash -lc `
    "grep '^MemAvailable:' /proc/meminfo | tr -s ' ' | cut -d ' ' -f 2")
$wslTotalKiB = [int64](wsl.exe -d Ubuntu-24.04 -- bash -lc `
    "grep '^MemTotal:' /proc/meminfo | tr -s ' ' | cut -d ' ' -f 2")
$wslAvailableBytes = $wslAvailableKiB * 1KB
$wslTotalBytes = $wslTotalKiB * 1KB
$wslRootFreeBytes = [int64](wsl.exe -d Ubuntu-24.04 -- bash -lc `
    "df -B1 --output=avail / | tail -n 1 | tr -d ' '")

$minimumMemoryBytes = 2GB
$minimumDiskBytes = 1GB
$hostMinimumAvailableBytes = ($cpuSamples |
    Measure-Object -Property available_memory_bytes -Minimum).Minimum
$functionalPass = $hostMinimumAvailableBytes -ge $minimumMemoryBytes -and `
    $wslAvailableBytes -ge $minimumMemoryBytes -and `
    $wslRootFreeBytes -ge $minimumDiskBytes
$cpuAverage = ($cpuSamples | Measure-Object -Property cpu_percent -Average).Average
$cpuMaximum = ($cpuSamples | Measure-Object -Property cpu_percent -Maximum).Maximum
$formalStabilityPass = $hostMinimumAvailableBytes -ge 4GB -and `
    $wslAvailableBytes -ge 4GB -and $cpuAverage -le 10 -and $cpuMaximum -le 20

$result = [ordered]@{
    schema = 'p1-resource-gate-v1'
    captured_at_local = [DateTimeOffset]::Now.ToString('o')
    host_available_bytes_initial = $hostAvailableBytes
    host_minimum_available_bytes = [int64]$hostMinimumAvailableBytes
    host_total_visible_bytes = [int64]$hostOs.TotalVisibleMemorySize * 1KB
    host_cpu_samples = $cpuSamples
    host_cpu_average_percent = [math]::Round($cpuAverage, 2)
    host_cpu_maximum_percent = [math]::Round($cpuMaximum, 2)
    wsl_total_bytes = $wslTotalBytes
    wsl_available_bytes = $wslAvailableBytes
    wsl_root_free_bytes = $wslRootFreeBytes
    functional_minimum_memory_bytes = $minimumMemoryBytes
    functional_minimum_disk_bytes = $minimumDiskBytes
    estimated_candidate_bytes = 3L * 4096L * 4096L * 8L
    estimated_candidate_plus_reference_bytes = 4L * 4096L * 4096L * 8L
    functional_gate = $(if ($functionalPass) { 'PASS' } else { 'REJECT' })
    formal_stability_gate = $(if ($formalStabilityPass) { 'PASS' } else { 'REJECT' })
    note = 'Functional PASS authorizes serial P1 pilot only; formal stability applies to later scored experiments.'
}

$result | ConvertTo-Json -Depth 5
if (-not $functionalPass) {
    exit 2
}
