param(
    [Parameter(Mandatory)][ValidateSet('HistoricalEnvironment','CurrentEnvironment','Base','Repeats','HeapMatrix','DerbyGC','OOMSummary','OOMRaw')]
    [string]$View,
    [switch]$Capture,
    [string]$Session = '2026-10-08'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
$evidenceDir = Join-Path $projectRoot "evidence\terminal_screenshots\$Session"
$imageDir = Join-Path $projectRoot "images\terminal\$Session"
New-Item -ItemType Directory -Path $evidenceDir,$imageDir -Force | Out-Null
$stem = $View.ToLowerInvariant()
$transcript = Join-Path $evidenceDir "$stem.txt"
$png = Join-Path $imageDir "$stem.png"
if (Test-Path -LiteralPath $transcript) { throw "Refusing to overwrite evidence: $transcript (choose a new -Session)." }

# Native APIs configure the real console; pixels below come only from the screen.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class A2Console {
    [StructLayout(LayoutKind.Sequential)] public struct Coord { public short X, Y; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct Font {
        public uint Size, Index; public Coord Dimensions; public int Family, Weight;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string Face;
    }
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int n);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool SetCurrentConsoleFontEx(IntPtr h, bool max, ref Font f);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int hgt, bool repaint);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect r);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int attribute, out Rect r, int size);
    public static void SetFont() {
        Font f = new Font { Size=(uint)Marshal.SizeOf(typeof(Font)), Dimensions=new Coord { X=0,Y=18 }, Family=54, Weight=400, Face="Consolas" };
        SetCurrentConsoleFontEx(GetStdHandle(-11),false,ref f);
    }
}
'@
[A2Console]::SetProcessDPIAware() | Out-Null
$handle = [A2Console]::GetConsoleWindow()
if ($Capture -and $handle -eq [IntPtr]::Zero) { throw 'No native console window; run in a visible conhost terminal.' }
if ($Capture) {
    Add-Type -AssemblyName System.Windows.Forms,System.Drawing
    [A2Console]::SetFont()
    $Host.UI.RawUI.BackgroundColor = 'Black'
    $Host.UI.RawUI.ForegroundColor = 'Gray'
    $Host.UI.RawUI.WindowTitle = "A2 SPECjvm2008 | $View"
    $bounds = [Windows.Forms.Screen]::PrimaryScreen.WorkingArea
    [A2Console]::ShowWindow($handle,9) | Out-Null
    [A2Console]::MoveWindow($handle,$bounds.Left+20,$bounds.Top+20,[Math]::Min(1940,$bounds.Width-40),$bounds.Height-40,$true) | Out-Null
    $maximum = $Host.UI.RawUI.MaxPhysicalWindowSize
    $columns = [Math]::Min(132,$maximum.Width)
    $rows = [Math]::Min(48,$maximum.Height)
    $initialWidth = [Math]::Max($columns,[Math]::Max($Host.UI.RawUI.BufferSize.Width,$Host.UI.RawUI.WindowSize.Width))
    $Host.UI.RawUI.BufferSize = [Management.Automation.Host.Size]::new($initialWidth,300)
    $Host.UI.RawUI.WindowSize = [Management.Automation.Host.Size]::new($columns,$rows)
    $Host.UI.RawUI.BufferSize = [Management.Automation.Host.Size]::new($columns,300)
    [A2Console]::SetForegroundWindow($handle) | Out-Null
}
Clear-Host
Start-Transcript -LiteralPath $transcript | Out-Null
$commands = [Collections.Generic.List[string]]::new()
$sources = [Collections.Generic.HashSet[string]]::new()
function Source([string]$path) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing source: $path" }
    [void]$sources.Add($path.Replace('\','/'))
}
function ReadCommand([string]$command,[scriptblock]$action) {
    $commands.Add($action.ToString().Trim())
    Write-Host "Read-only step: $command" -ForegroundColor Cyan
    & $action | Out-Host
    if ($LASTEXITCODE -and $command -match '^python|^wsl') { throw "Read-only command failed: $LASTEXITCODE" }
}
Write-Host "A2 SPECjvm2008 - $View" -ForegroundColor White
Write-Host "PS $projectRoot> .\scripts\screenshots\show_terminal_evidence.ps1 -View $View$(if ($Capture) {' -Capture'}) -Session $Session"
Write-Host "Collection time: $((Get-Date).ToString('o'))"
Write-Host $(if ($View -eq 'CurrentEnvironment') {'CURRENT CHECK ONLY; not historical measurement evidence.'} else {'READING HISTORICAL EXPERIMENT FILES; dates come from original sources. No benchmark rerun.'})
Write-Host ''
switch ($View) {
    HistoricalEnvironment {
        Source 'environment/environment_info.txt'; Source 'logs/base_run.log'
        ReadCommand "Select-String environment/environment_info.txt -Pattern 'Collection time|^2026-|^Linux |^Description:|^CPU\(s\):|^Model name:|^Thread\(s\)|^Core\(s\)|^Socket\(s\)|^Mem:|^Swap:|^openjdk |^OpenJDK |^javac |^JAVA_HOME=|^CLASSPATH='" {
            Select-String -LiteralPath environment/environment_info.txt -Pattern 'Collection time|^2026-|^Linux |^Description:|^CPU\(s\):|^Model name:|^Thread\(s\)|^Core\(s\)|^Socket\(s\)|^Mem:|^Swap:|^openjdk |^OpenJDK |^javac |^JAVA_HOME=|^CLASSPATH=' | ForEach-Object { $_.Line }
        }
        ReadCommand 'Get-Content logs/base_run.log -TotalCount 8; Select-String logs/base_run.log -Pattern "^END_TIME=|^EXIT_STATUS="' {
            Get-Content -LiteralPath logs/base_run.log -TotalCount 8
            Select-String -LiteralPath logs/base_run.log -Pattern '^END_TIME=|^EXIT_STATUS=' | ForEach-Object { $_.Line }
        }
    }
    CurrentEnvironment {
        ReadCommand 'Get-CimInstance Win32_OperatingSystem | Select Caption,Version,LastBootUpTime' {
            Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,LastBootUpTime | Format-List
        }
        ReadCommand 'wsl -d Ubuntu-24.04 -- bash -c "date -Is; uname -a; lsb_release -ds; lscpu | CPU fields; free -h"' {
            wsl -d Ubuntu-24.04 -- bash -c 'date -Is; uname -a; lsb_release -ds; lscpu | grep -E "^CPU\(s\):|^Model name:|^Thread\(s\)|^Core\(s\)|^Socket\(s\)"; free -h'
        }
        ReadCommand 'wsl -d Ubuntu-24.04 -- bash -c "printenv JAVA_HOME CLASSPATH; command -v java; java -version; /home/gubingren/java/java-se-7u75-ri/bin/java -version"' {
            wsl -d Ubuntu-24.04 -- bash -c 'printf "Current shell JAVA_HOME=%s CLASSPATH=%s\n" "$JAVA_HOME" "$CLASSPATH"; command -v java; java -version 2>&1; printf "Historical measurement JDK executable check:\n"; /home/gubingren/java/java-se-7u75-ri/bin/java -version 2>&1'
        }
        Write-Host 'This current check does not replace environment/environment_info.txt.'
    }
    Base {
        Source 'specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt'
        Source 'specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw'
        Source 'logs/base_run.log'
        ReadCommand 'python -B scripts/analysis/build_core_data.py --check' { python -B scripts/analysis/build_core_data.py --check }
        ReadCommand 'Get-Content specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt -TotalCount 22' {
            Get-Content -LiteralPath specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt -TotalCount 22
        }
    }
    Repeats {
        foreach ($id in 8..10) { foreach ($ext in 'raw','txt') { Source ('specjvm2008/results/SPECjvm2008.{0:000}/SPECjvm2008.{0:000}.{1}' -f $id,$ext) } }
        ReadCommand 'python -B scripts/analysis/build_core_data.py --check' { python -B scripts/analysis/build_core_data.py --check }
        ReadCommand 'python -B scripts/screenshots/summarize_repeats.py' { python -B scripts/screenshots/summarize_repeats.py }
    }
    HeapMatrix {
        Source 'analysis/jvm_parameter/heap_parameter_results.csv'; Source 'analysis/jvm_parameter/heap_parameter_summary.csv'
        ReadCommand 'python -B scripts/jvm_parameter/build_optional_data.py --check' { python -B scripts/jvm_parameter/build_optional_data.py --check }
        ReadCommand 'Import-Csv analysis/jvm_parameter/heap_parameter_summary.csv | Select workload,heap_config,valid_n,invalid_n,mean_score_ops_per_min,cv_score_percent | Format-Table' {
            Import-Csv analysis/jvm_parameter/heap_parameter_summary.csv | Select-Object workload,heap_config,valid_n,invalid_n,mean_score_ops_per_min,cv_score_percent | Format-Table -AutoSize
        }
        ReadCommand 'Import-Csv analysis/jvm_parameter/heap_parameter_results.csv | Group-Object status | Select Name,Count' {
            Import-Csv analysis/jvm_parameter/heap_parameter_results.csv | Group-Object status | Select-Object Name,Count | Format-Table -AutoSize
        }
        Write-Host 'Blank scores are failures, NOT zero performance. Each cell has three independent JVM attempts.'
    }
    DerbyGC {
        Source 'analysis/jvm_parameter/gc_measurement_summary.csv'; Source 'analysis/jvm_parameter/heap_parameter_results.csv'
        ReadCommand 'python -B scripts/jvm_parameter/build_enhancement_data.py --check' { python -B scripts/jvm_parameter/build_enhancement_data.py --check }
        Write-Host 'Window: ESTIMATED measurement phase; +/-1 s uncertain boundary events excluded.' -ForegroundColor Yellow
        ReadCommand 'Import-Csv analysis/jvm_parameter/gc_measurement_summary.csv | Where workload -eq derby | Select heap_config,valid_n,score,FullGC,pause,pre%,post%' {
            Import-Csv analysis/jvm_parameter/gc_measurement_summary.csv | Where-Object workload -eq derby | Select-Object heap_config,valid_n,@{n='score_ops/min';e={$_.mean_score_ops_per_min}},@{n='FullGC_mean';e={$_.mean_measurement_full_gc_count}},@{n='pause_s_mean';e={$_.mean_measurement_gc_pause_s}},@{n='pre_heap_%';e={$_.mean_measurement_pre_gc_max_heap_percent}},@{n='post_heap_%';e={$_.mean_measurement_post_gc_max_heap_percent}} | Format-Table -AutoSize
        }
        Write-Host 'Separate window: WHOLE JAVA PROCESS (includes warmup; valid runs only).' -ForegroundColor Yellow
        ReadCommand 'Import-Csv analysis/jvm_parameter/heap_parameter_results.csv | Where workload -eq derby | Group heap_config | compute valid means(gc_full_count,gc_time_s)' {
            Import-Csv analysis/jvm_parameter/heap_parameter_results.csv | Where-Object workload -eq derby | Group-Object heap_config | ForEach-Object {
                $valid = @($_.Group | Where-Object status -eq valid)
                [pscustomobject]@{heap=$_.Name;valid=$valid.Count;FullGC_mean=$(if ($valid.Count) { '{0:F3}' -f ($valid | Measure-Object gc_full_count -Average).Average } else {'N/A'});pause_s_mean=$(if ($valid.Count) { '{0:F6}' -f ($valid | Measure-Object gc_time_s -Average).Average } else {'N/A'})}
            } | Format-Table -AutoSize
        }
        Write-Host '512 MiB has no valid measured score; do not count its failed warmup as measurement.'
    }
    OOMSummary {
        Source 'analysis/jvm_parameter/oom_reverification_results.csv'
        ReadCommand 'python -B scripts/jvm_parameter/build_oom_reverification.py --check' { python -B scripts/jvm_parameter/build_oom_reverification.py --check }
        ReadCommand 'Import-Csv analysis/jvm_parameter/oom_reverification_results.csv | Select workload,heap_config,run_id,Result,JavaExit,ReporterExit,OOM,NOT_VALID,reproduced' {
            Import-Csv analysis/jvm_parameter/oom_reverification_results.csv | Select-Object workload,heap_config,run_id,@{n='Result';e={$_.verification_result_id}},@{n='JavaExit';e={$_.verification_java_exit_status}},@{n='ReporterExit';e={$_.verification_reporter_exit_status}},@{n='OOM';e={$_.verification_oom_occurrences}},@{n='NOT_VALID';e={$_.verification_not_valid}},@{n='reproduced';e={$_.failure_reproduced}} | Format-Table -AutoSize
        }
        ReadCommand 'python -B scripts/jvm_parameter/verify_oom_reverification.py' { python -B scripts/jvm_parameter/verify_oom_reverification.py }
        Write-Host 'Independent namespace: specjvm2008/verification_results/. Original 48-attempt matrix unchanged.'
        Write-Host 'Watchdog: 900 s; exit 124 = timeout, 255 = nonzero failure, 0 alone does not establish validity.'
    }
    OOMRaw {
        $log = 'logs/jvm_parameter/oom_reverification/oomverify__scimark_fft_large__xmx512m__r1.log'
        $meta = $log -replace '\.log$','.meta'
        Source $log; Source $meta
        Source 'specjvm2008/verification_results/SPECjvm2008.069/SPECjvm2008.069.txt'
        ReadCommand "Select-String $log -Pattern '^SOURCE_RUN_KEY=|^START_TIME=|^COMMAND=|^JAVA_EXIT|^END_TIME=|NOT VALID|OutOfMemoryError' (first OOM only)" {
            $shownOOM = $false
            Select-String -LiteralPath $log -Pattern '^SOURCE_RUN_KEY=|^START_TIME=|^COMMAND=|^JAVA_EXIT|^END_TIME=|NOT VALID|OutOfMemoryError' | ForEach-Object {
                if ($_.Line -match 'OutOfMemoryError') { if ($shownOOM) { return }; $shownOOM = $true }
                "{0}: {1}" -f $_.LineNumber,$_.Line
            }
        }
        ReadCommand "Select-String $meta -Pattern '^result_id=|^heap_config=|^java_exit_status=|^reporter_exit_status=|^start_time=|^end_time='" {
            Select-String -LiteralPath $meta -Pattern '^result_id=|^heap_config=|^java_exit_status=|^reporter_exit_status=|^start_time=|^end_time=' | ForEach-Object { $_.Line }
        }
        ReadCommand 'Select-String specjvm2008/verification_results/SPECjvm2008.069/SPECjvm2008.069.txt -Pattern "Run is|NOT VALID|Composite"' {
            Select-String -LiteralPath specjvm2008/verification_results/SPECjvm2008.069/SPECjvm2008.069.txt -Pattern 'Run is|NOT VALID|Composite' | ForEach-Object { $_.Line }
        }
        Write-Host 'Evidence above is a failed historical run despite Java exit=0; no valid measured score.'
    }
}
# Index all original inputs backing CSV summaries as well as the visible sources.
$csv = switch ($View) { HeapMatrix {'analysis/jvm_parameter/heap_parameter_results.csv'} DerbyGC {'analysis/jvm_parameter/heap_parameter_results.csv'} OOMSummary {'analysis/jvm_parameter/oom_reverification_results.csv'} }
if ($csv) {
    foreach ($row in (Import-Csv $csv)) {
        if ($View -eq 'DerbyGC' -and $row.workload -ne 'derby') { continue }
        foreach ($field in 'raw_path','txt_path','run_log_path','gc_log_path') { if ($row.$field) { Source $row.$field } }
    }
}
Write-Host ''
Write-Host 'Read-only evidence display complete. Original data have not been rewritten.' -ForegroundColor Green
Stop-Transcript | Out-Null
$renderedRows = $Host.UI.RawUI.CursorPosition.Y + 1
$captured = $false
$rectangle = $null
if ($Capture) {
    if (Test-Path -LiteralPath $png) { throw "Refusing to overwrite screenshot: $png" }
    if ($renderedRows -ge $Host.UI.RawUI.WindowSize.Height) { throw "Output exceeds visible rows ($renderedRows); split this view before capturing." }
    $Host.UI.RawUI.WindowSize = [Management.Automation.Host.Size]::new($columns,$renderedRows+1)
    $Host.UI.RawUI.WindowPosition = [Management.Automation.Host.Coordinates]::new(0,0)
    [A2Console]::SetForegroundWindow($handle) | Out-Null
    Start-Sleep -Milliseconds 1800
    if ([A2Console]::GetForegroundWindow() -ne $handle) { throw 'Console is not foreground; screen capture aborted.' }
    $rect = [A2Console+Rect]::new()
    if ([A2Console]::DwmGetWindowAttribute($handle,9,[ref]$rect,[Runtime.InteropServices.Marshal]::SizeOf($rect)) -ne 0) {
        [A2Console]::GetWindowRect($handle,[ref]$rect) | Out-Null
    }
    $bitmap = [Drawing.Bitmap]::new($rect.Right-$rect.Left,$rect.Bottom-$rect.Top)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($rect.Left,$rect.Top,0,0,$bitmap.Size,[Drawing.CopyPixelOperation]::SourceCopy)
        $bitmap.Save($png,[Drawing.Imaging.ImageFormat]::Png)
    } finally { $graphics.Dispose(); $bitmap.Dispose() }
    $captured = $true
    $rectangle = @{left=$rect.Left;top=$rect.Top;right=$rect.Right;bottom=$rect.Bottom}
}
$sourceHashes = @($sources | Sort-Object | ForEach-Object { [ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant()} })
$metadata = [ordered]@{view=$View;collected_at=(Get-Date).ToString('o');historical=($View -ne 'CurrentEnvironment');project_root=$projectRoot;display_script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant();commands=@($commands);sources=$sourceHashes;transcript="evidence/terminal_screenshots/$Session/$stem.txt";native_screen_capture=$captured;capture_api=$(if ($captured) {'System.Drawing.Graphics.CopyFromScreen (Windows desktop pixels; DWM visible window bounds)'} else {$null});window_handle=$handle.ToInt64();window_rect=$rectangle;rendered_rows=$renderedRows;visible_rows=$Host.UI.RawUI.WindowSize.Height;screenshot=$(if ($captured) {"images/terminal/$Session/$stem.png"} else {$null});screenshot_sha256=$(if ($captured) {(Get-FileHash -LiteralPath $png -Algorithm SHA256).Hash.ToLowerInvariant()} else {$null})}
$metadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidenceDir "$stem.json") -Encoding utf8
if ($Capture) { Read-Host "Native screenshot saved. Press Enter to close this terminal" | Out-Null }
