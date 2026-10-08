$ErrorActionPreference = 'Continue'

function Invoke-Recorded {
    param([string]$Label, [scriptblock]$Command)
    Write-Output "`n$ $Label"
    & $Command 2>&1
    Write-Output "[exit_code=$LASTEXITCODE]"
}

Write-Output "collected_at_local=$([DateTimeOffset]::Now.ToString('o'))"
Write-Output "timezone=$([TimeZoneInfo]::Local.Id)"

Write-Output "`n$ Windows version registry fields"
$windowsVersion = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
[pscustomobject]@{
    DisplayVersion = $windowsVersion.DisplayVersion
    CurrentBuild = $windowsVersion.CurrentBuild
    UBR = $windowsVersion.UBR
} | Format-List | Out-String -Width 240 | Write-Output

Write-Output "`n$ Get-CimInstance Win32_OperatingSystem"
Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, BuildNumber, OSArchitecture, LastBootUpTime |
    Format-List | Out-String -Width 240 | Write-Output

Write-Output "`n$ Get-CimInstance Win32_ComputerSystem"
Get-CimInstance Win32_ComputerSystem |
    Select-Object Manufacturer, Model, SystemType, HypervisorPresent,
        @{Name='TotalPhysicalMemoryBytes';Expression={$_.TotalPhysicalMemory}} |
    Format-List | Out-String -Width 240 | Write-Output

Write-Output "`n$ Get-CimInstance Win32_Processor"
Get-CimInstance Win32_Processor |
    Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors,
        MaxClockSpeed, CurrentClockSpeed, L2CacheSize, L3CacheSize, VirtualizationFirmwareEnabled |
    Format-List | Out-String -Width 240 | Write-Output

Write-Output "`n$ Get-CimInstance Win32_CacheMemory"
Get-CimInstance Win32_CacheMemory |
    Select-Object Level, InstalledSize, MaxCacheSize, NumberOfBlocks |
    Format-List | Out-String -Width 240 | Write-Output

Write-Output "`n$ Get-CimInstance Win32_OperatingSystem memory fields"
Get-CimInstance Win32_OperatingSystem |
    Select-Object TotalVisibleMemorySize, FreePhysicalMemory, TotalVirtualMemorySize, FreeVirtualMemory |
    Format-List | Out-String -Width 240 | Write-Output

Write-Output "`n$ five one-second CPU and available-memory samples"
$samples = 1..5 | ForEach-Object {
    $cpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor |
        Where-Object Name -eq '_Total'
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    [pscustomobject]@{
        Timestamp = [DateTimeOffset]::Now.ToString('o')
        CpuPercent = $cpu.PercentProcessorTime
        AvailableMemoryMiB = [math]::Round($memory.AvailableBytes / 1MB, 1)
    }
    Start-Sleep -Seconds 1
}
$samples | Format-Table -AutoSize | Out-String -Width 240 | Write-Output

Write-Output "`n$ current process affinity"
$process = Get-Process -Id $PID
[pscustomobject]@{
    ProcessorCount = [Environment]::ProcessorCount
    ProcessorAffinityMask = ('0x{0:X}' -f $process.ProcessorAffinity.ToInt64())
} | Format-List | Out-String -Width 240 | Write-Output

Write-Output "`n$ Get-PSDrive E"
Get-PSDrive -Name E | Select-Object Name, Used, Free, Root |
    Format-List | Out-String -Width 240 | Write-Output

Invoke-Recorded 'powercfg /getactivescheme' { powercfg /getactivescheme }
Invoke-Recorded 'powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN' {
    powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN
}
Invoke-Recorded 'powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX' {
    powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX
}

Write-Output "`n$ Get-CimInstance Win32_Battery"
Get-CimInstance Win32_Battery | Select-Object BatteryStatus, EstimatedChargeRemaining |
    Format-List | Out-String -Width 240 | Write-Output
Invoke-Recorded 'wsl.exe -d Ubuntu-24.04 -- bash -lc "printf distro/version and uname"' {
    wsl.exe -d Ubuntu-24.04 -- bash -lc 'printf "WSL_DISTRO_NAME=%s\n" "$WSL_DISTRO_NAME"; uname -srmo'
}

foreach ($tool in @('gcc','clang','python','git','gh','make','cmake','wsl')) {
    Write-Output "`n## $tool"
    $command = Get-Command $tool -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        Write-Output 'path=<not found>'
    } else {
        Write-Output "path=$($command.Source)"
    }
}

Invoke-Recorded 'python --version' { python --version }
Invoke-Recorded 'git --version' { git --version }
if (Get-Command cmake -ErrorAction SilentlyContinue) {
    Invoke-Recorded 'cmake --version' { cmake --version }
} else {
    Write-Output "`n$ cmake --version"
    Write-Output 'cmake=<not found>'
    Write-Output '[exit_code=127]'
}
