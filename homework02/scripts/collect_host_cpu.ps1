$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$outputPath = Join-Path $projectRoot 'environment\host_cpu_comparison.txt'

@(
    "CollectionTime=$([DateTimeOffset]::Now.ToString('o'))"
    'Command=Get-CimInstance Win32_Processor | Select-Object Name,CurrentClockSpeed,MaxClockSpeed,NumberOfCores,NumberOfLogicalProcessors'
    (Get-CimInstance Win32_Processor |
        Select-Object Name, CurrentClockSpeed, MaxClockSpeed, NumberOfCores, NumberOfLogicalProcessors |
        Format-List | Out-String)
    'Note=Clock speeds are a Windows WMI snapshot in MHz, not a measured frequency during SPECjvm2008.'
    'Command=Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber'
    (Get-CimInstance Win32_OperatingSystem |
        Select-Object Caption, Version, BuildNumber |
        Format-List | Out-String)
) | Set-Content -LiteralPath $outputPath -Encoding utf8

Get-Content -LiteralPath $outputPath
