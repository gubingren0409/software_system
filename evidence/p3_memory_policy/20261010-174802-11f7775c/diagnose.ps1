$ErrorActionPreference = 'Stop'
$env:PSModulePath = 'C:\Windows\System32\WindowsPowerShell\v1.0\Modules'
$ready = wsl.exe -d Ubuntu-24.04 -- cat /proc/uptime
$readyExit = $LASTEXITCODE
if ($readyExit -ne 0) { throw 'WSL readiness query failed' }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class MemoryReadOnly {
  [StructLayout(LayoutKind.Sequential)] public struct MEMORYSTATUSEX {
    public uint length, load; public ulong totalPhys, availPhys, totalPage, availPage, totalVirtual, availVirtual, availExtended;
  }
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool GlobalMemoryStatusEx(ref MEMORYSTATUSEX s);
  public static MEMORYSTATUSEX Read() { var s = new MEMORYSTATUSEX(); s.length=(uint)Marshal.SizeOf(s);
    if(!GlobalMemoryStatusEx(ref s)) throw new Exception("GlobalMemoryStatusEx unavailable"); return s; }
}
'@
$windowStart = [DateTimeOffset]::Now.ToString('o')
$samples = @()
for ($index=0; $index -lt 5; $index++) {
    $start = [DateTimeOffset]::Now.ToString('o')
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    $cpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total'
    $other = [MemoryReadOnly]::Read()
    $vmmem = @(Get-Process -Name VmmemWSL,Vmmem -ErrorAction SilentlyContinue | ForEach-Object {
        [ordered]@{pid=$_.Id; name=$_.ProcessName; working_set_bytes=$_.WorkingSet64; private_bytes=$_.PrivateMemorySize64}
    })
    $meminfo = @(wsl.exe -d Ubuntu-24.04 -- cat /proc/meminfo)
    $meminfoExit = $LASTEXITCODE
    $samples += [ordered]@{
        index=$index; start_local=$start; end_local=[DateTimeOffset]::Now.ToString('o')
        host_available_bytes=[int64]$memory.AvailableBytes; host_committed_bytes=[int64]$memory.CommittedBytes
        host_commit_limit_bytes=[int64]$memory.CommitLimit; host_pages_per_second=[int64]$memory.PagesPersec
        host_page_reads_per_second=[int64]$memory.PageReadsPersec; host_page_writes_per_second=[int64]$memory.PageWritesPersec
        cpu_percent=[double]$cpu.PercentProcessorTime; counter_timestamp_sys100ns=[string]$memory.Timestamp_Sys100NS
        global_memory_status_ex=[ordered]@{available_physical_bytes=$other.availPhys; total_physical_bytes=$other.totalPhys; available_page_file_bytes=$other.availPage; total_page_file_bytes=$other.totalPage}
        vmmem=$(if ($vmmem.Count) {$vmmem} else {'unknown: no readable VmmemWSL/Vmmem process'})
        wsl_meminfo=$meminfo; wsl_meminfo_exit_code=$meminfoExit
    }
    if ($index -lt 4) { Start-Sleep -Seconds 1 }
}
$windowEnd = [DateTimeOffset]::Now.ToString('o')
$version = @(wsl.exe --version); $versionExit = $LASTEXITCODE
$wslconfigPath = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.wslconfig'
$configuration = 'unknown: .wslconfig absent'
if (Test-Path -LiteralPath $wslconfigPath) {
    $configuration = [ordered]@{sha256=(Get-FileHash -LiteralPath $wslconfigPath -Algorithm SHA256).Hash.ToLower(); relevant_lines=@(Get-Content -LiteralPath $wslconfigPath | Where-Object {$_ -match '^\s*(\[wsl2\]|\[experimental\]|memory\s*=|autoMemoryReclaim\s*=|pageReporting\s*=|swap\s*=)'})}
}
[ordered]@{schema='p3-memory-diagnosis-v1'; declared_groups=1; cold_start_before_captured=$false;
    system_settings_modified=$false; ready_uptime=$ready; window_start_local=$windowStart; window_end_local=$windowEnd;
    samples=$samples; wsl_version=$version; wsl_version_exit_code=$versionExit; existing_wslconfig=$configuration;
    caveat='Paired samples have explicit start/end boundaries, not simultaneous instants. No cold startup baseline; no Windows+Vmmem capacity summation or causal claim.'
} | ConvertTo-Json -Depth 10
