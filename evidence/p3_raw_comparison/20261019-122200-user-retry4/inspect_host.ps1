$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$snapshotStart = Get-Date -Format o
$memoryReading = 'unknown'
$snapshotErrors = @()
try {
    $memoryReading = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory |
        Select-Object AvailableBytes,CommittedBytes,CommitLimit,PagesPersec,PageReadsPersec
} catch { $snapshotErrors += $_.Exception.Message }
$topProcesses = @(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 Id,ProcessName,WorkingSet64,PrivateMemorySize64)
$vmmemProcesses = @(Get-Process -Name VmmemWSL,Vmmem -ErrorAction SilentlyContinue |
    Select-Object Id,ProcessName,WorkingSet64,PrivateMemorySize64)
[ordered]@{
    purpose = 'One read-only occupancy snapshot during this continuation; not an additional gate'
    started_at = $snapshotStart
    ended_at = (Get-Date -Format o)
    memory = $memoryReading
    top_working_sets = $topProcesses
    vmmem = $vmmemProcesses
    errors = $snapshotErrors
} | ConvertTo-Json -Depth 6
