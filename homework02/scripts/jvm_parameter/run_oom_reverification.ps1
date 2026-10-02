$ErrorActionPreference = 'Stop'

$projectDir = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$wslProjectDir = (& wsl.exe -d Ubuntu-24.04 -- wslpath -u ($projectDir.Replace('\', '/'))).Trim()
if ($LASTEXITCODE -ne 0 -or -not $wslProjectDir.StartsWith('/mnt/e/')) {
    throw "Could not resolve repository inside WSL: $projectDir"
}
$runner = "$wslProjectDir/scripts/jvm_parameter/run_oom_reverification_one.sh"
$distro = 'Ubuntu-24.04'

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class OomReverificationAwakeState {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
'@
$esContinuous = [uint32]::Parse('80000000', [Globalization.NumberStyles]::HexNumber)
$esSystemRequired = [uint32]0x00000001

$officialRaw = Join-Path $projectDir 'specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw'
$matrixCsv = Join-Path $projectDir 'analysis/jvm_parameter/heap_parameter_results.csv'
$expectedRawHash = '4AE651E312061D09760743AB9908129B633E9CE1E5B5B296C13D4A30605E05AD'
$matrixHashBefore = (Get-FileHash -LiteralPath $matrixCsv -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $officialRaw -Algorithm SHA256).Hash -ne $expectedRawHash) {
    throw 'Formal SPECjvm2008.007 raw differs before reverification.'
}

$attempts = @(
    [pscustomobject]@{ Workload = 'derby'; Heap = 'xmx512m'; Repetition = 1 },
    [pscustomobject]@{ Workload = 'derby'; Heap = 'xmx512m'; Repetition = 2 },
    [pscustomobject]@{ Workload = 'derby'; Heap = 'xmx512m'; Repetition = 3 },
    [pscustomobject]@{ Workload = 'scimark.fft.large'; Heap = 'xmx512m'; Repetition = 1 },
    [pscustomobject]@{ Workload = 'scimark.fft.large'; Heap = 'xmx1024m'; Repetition = 1 },
    [pscustomobject]@{ Workload = 'scimark.fft.large'; Heap = 'xmx512m'; Repetition = 2 },
    [pscustomobject]@{ Workload = 'scimark.fft.large'; Heap = 'xmx1024m'; Repetition = 2 },
    [pscustomobject]@{ Workload = 'scimark.fft.large'; Heap = 'xmx512m'; Repetition = 3 },
    [pscustomobject]@{ Workload = 'scimark.fft.large'; Heap = 'xmx1024m'; Repetition = 3 }
)

$awakeResult = [OomReverificationAwakeState]::SetThreadExecutionState($esContinuous -bor $esSystemRequired)
if ($awakeResult -eq 0) { throw 'Could not prevent host sleep during reverification.' }
try {
    foreach ($attempt in $attempts) {
        $slug = $attempt.Workload.Replace('.', '_')
        $key = "oomverify__${slug}__$($attempt.Heap)__r$($attempt.Repetition)"
        $meta = Join-Path $projectDir "logs/jvm_parameter/oom_reverification/$key.meta"
        if (Test-Path -LiteralPath $meta) {
            Write-Output "SKIP_EXISTING_REVERIFICATION=$key"
            continue
        }

        $windowsEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        & wsl.exe -d $distro -u root -- date -s "@$windowsEpoch" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Clock sync failed before $key" }
        $wslEpoch = [long](& wsl.exe -d $distro -- date +%s)
        $windowsEpochAfter = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $clockDifference = [math]::Abs($windowsEpochAfter - $wslEpoch)
        if ($clockDifference -gt 3) { throw "Clock difference $clockDifference seconds before $key" }

        Write-Output "START_REVERIFICATION=$key CLOCK_DIFFERENCE_SECONDS=$clockDifference"
        & wsl.exe -d $distro -- bash $runner $wslProjectDir $attempt.Workload $attempt.Heap ([string]$attempt.Repetition)
        if ($LASTEXITCODE -ne 0) { throw "Runner failed for $key; exit $LASTEXITCODE" }
        if (-not (Test-Path -LiteralPath $meta)) { throw "Runner returned without metadata for $key" }
    }
}
finally {
    [void][OomReverificationAwakeState]::SetThreadExecutionState($esContinuous)
    Write-Output 'SLEEP_PREVENTION=released'
}

$metaFiles = @(Get-ChildItem -LiteralPath (Join-Path $projectDir 'logs/jvm_parameter/oom_reverification') -Filter '*.meta')
if ($metaFiles.Count -ne 9) { throw "Expected 9 reverification metadata files, found $($metaFiles.Count)." }
if ((Get-FileHash -LiteralPath $officialRaw -Algorithm SHA256).Hash -ne $expectedRawHash) {
    throw 'Formal SPECjvm2008.007 raw changed during reverification.'
}
if ((Get-FileHash -LiteralPath $matrixCsv -Algorithm SHA256).Hash -ne $matrixHashBefore) {
    throw 'Original 48-attempt matrix changed during reverification.'
}
Write-Output 'OOM_REVERIFICATION_9_ATTEMPTS_CAPTURED=true'
Write-Output 'FORMAL_007_UNCHANGED=true'
Write-Output 'ORIGINAL_MATRIX_UNCHANGED=true'
