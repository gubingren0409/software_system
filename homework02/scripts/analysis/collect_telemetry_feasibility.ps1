$ErrorActionPreference = 'Continue'

Write-Output 'PURPOSE=Present-time telemetry feasibility check; not historical benchmark telemetry'
Write-Output "COLLECTED_AT=$((Get-Date).ToString('o'))"
Write-Output 'HOST_PROCESSOR_CIM='
Get-CimInstance Win32_Processor |
    Select-Object Name,CurrentClockSpeed,MaxClockSpeed,LoadPercentage,NumberOfCores,NumberOfLogicalProcessors |
    Format-List | Out-String | Write-Output
Write-Output 'ACTIVE_POWER_SCHEME='
powercfg /getactivescheme
Write-Output 'ACPI_TEMPERATURE='
try {
    Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop |
        Select-Object InstanceName,CurrentTemperature | Format-List | Out-String | Write-Output
} catch {
    Write-Output "UNAVAILABLE: $($_.Exception.Message)"
}
Write-Output 'WSL_FEASIBILITY='
& wsl.exe -d Ubuntu-24.04 -- bash -lc 'date --iso-8601=seconds; uname -r; command -v perf; perf --version; command -v /usr/bin/time; cat /proc/loadavg; free -h; if compgen -G "/sys/class/thermal/thermal_zone*" >/dev/null; then echo THERMAL_ZONES=available; else echo THERMAL_ZONES=unavailable; fi; if [[ -d /sys/devices/system/cpu/cpu0/cpufreq ]]; then echo CPUFREQ_SYSFS=available; else echo CPUFREQ_SYSFS=unavailable; fi'
Write-Output "WSL_EXIT_STATUS=$LASTEXITCODE"
