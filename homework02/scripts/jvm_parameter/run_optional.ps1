$ErrorActionPreference = 'Stop'

$projectDir = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$wslProjectDir = (& wsl.exe -d Ubuntu-24.04 -- wslpath -u ($projectDir.Replace('\', '/'))).Trim()
if ($LASTEXITCODE -ne 0 -or -not $wslProjectDir.StartsWith('/mnt/e/')) {
    throw "Could not resolve repository inside WSL: $projectDir"
}
$runner = "$wslProjectDir/scripts/jvm_parameter/run_one.sh"
$distro = 'Ubuntu-24.04'

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class OptionalExperimentAwakeState {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
'@
$esContinuous = [uint32]::Parse('80000000', [Globalization.NumberStyles]::HexNumber)
$esSystemRequired = [uint32]0x00000001

$officialRaw = Join-Path $projectDir 'specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw'
$expectedHash = '4AE651E312061D09760743AB9908129B633E9CE1E5B5B296C13D4A30605E05AD'
if ((Get-FileHash -LiteralPath $officialRaw -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'Formal SPECjvm2008.007 raw hash differs from the pre-experiment value.'
}

$workloads = @('compress', 'derby', 'sunflow', 'scimark.fft.large')
$orders = @(
    @('default', 'xmx512m', 'xmx1024m', 'xmx2560m'),
    @('xmx2560m', 'xmx1024m', 'xmx512m', 'default'),
    @('xmx512m', 'default', 'xmx2560m', 'xmx1024m')
)
$attempts = foreach ($workload in $workloads) {
    for ($i = 0; $i -lt $orders.Count; $i++) {
        foreach ($heap in $orders[$i]) {
            [pscustomobject]@{ Workload = $workload; Heap = $heap; Repetition = $i + 1 }
        }
    }
}

$awakeResult = [OptionalExperimentAwakeState]::SetThreadExecutionState($esContinuous -bor $esSystemRequired)
if ($awakeResult -eq 0) { throw 'Could not prevent host sleep for the optional experiment.' }
try {
    foreach ($attempt in $attempts) {
        $slug = $attempt.Workload.Replace('.', '_')
        $key = "${slug}__$($attempt.Heap)__r$($attempt.Repetition)"
        $meta = Join-Path $projectDir "logs/jvm_parameter/$($attempt.Heap)/$key.meta"
        if (Test-Path -LiteralPath $meta) {
            Write-Output "SKIP_EXISTING_ATTEMPT=$key"
            continue
        }

        # WSL's wall clock can drift over a long sequential run. Sync only between JVM processes.
        $windowsEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        & wsl.exe -d $distro -u root -- date -s "@$windowsEpoch" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Clock sync failed before $key" }
        $wslEpoch = [long](& wsl.exe -d $distro -- date +%s)
        $windowsEpochAfter = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $clockDifference = [math]::Abs($windowsEpochAfter - $wslEpoch)
        if ($clockDifference -gt 3) { throw "Clock difference $clockDifference seconds before $key" }

        Write-Output "START_ATTEMPT=$key WINDOWS_EPOCH=$windowsEpochAfter WSL_EPOCH=$wslEpoch CLOCK_DIFFERENCE_SECONDS=$clockDifference"
        & wsl.exe -d $distro -- bash $runner $wslProjectDir $attempt.Workload $attempt.Heap ([string]$attempt.Repetition)
        if ($LASTEXITCODE -ne 0) { throw "Runner failed before completing evidence capture for $key; exit $LASTEXITCODE" }
        if (-not (Test-Path -LiteralPath $meta)) { throw "Runner returned without metadata for $key" }
    }
}
finally {
    [void][OptionalExperimentAwakeState]::SetThreadExecutionState($esContinuous)
    Write-Output 'SLEEP_PREVENTION=released'
}

$plannedMeta = @($attempts | ForEach-Object {
    $slug = $_.Workload.Replace('.', '_')
    $key = "${slug}__$($_.Heap)__r$($_.Repetition)"
    Join-Path $projectDir "logs/jvm_parameter/$($_.Heap)/$key.meta"
})
$missingMeta = @($plannedMeta | Where-Object { -not (Test-Path -LiteralPath $_) })
Write-Output "PLANNED_ATTEMPT_METADATA_COUNT=$(($plannedMeta.Count - $missingMeta.Count))"
if ($missingMeta.Count -ne 0) {
    throw "Not all 48 planned attempt metadata files are present; missing $($missingMeta.Count)."
}
if ((Get-FileHash -LiteralPath $officialRaw -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'Formal SPECjvm2008.007 raw changed during the optional experiment.'
}
Write-Output 'OPTIONAL_48_ATTEMPTS_CAPTURED=true'
