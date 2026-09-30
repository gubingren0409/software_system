$ErrorActionPreference = 'Stop'
$runScript = '/mnt/e/software_system/A2/homework02/scripts/run_parameter_base_only.sh'

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ParameterBaseAwakeState {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
'@

$esContinuous = [uint32]::Parse('80000000', [Globalization.NumberStyles]::HexNumber)
$esSystemRequired = [uint32]0x00000001
$runExit = 1

try {
    $windowsEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    & wsl.exe -d Ubuntu-24.04 -u root -- date -s "@$windowsEpoch"
    if ($LASTEXITCODE -ne 0) { throw 'Failed to synchronize the WSL clock.' }

    $wslEpoch = [long](& wsl.exe -d Ubuntu-24.04 -- date +%s)
    $windowsEpochAfter = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $clockDifference = [math]::Abs($windowsEpochAfter - $wslEpoch)
    "WINDOWS_EPOCH=$windowsEpochAfter"
    "WSL_EPOCH=$wslEpoch"
    "CLOCK_DIFFERENCE_SECONDS=$clockDifference"
    if ($clockDifference -gt 3) { throw "Windows and WSL clocks differ by $clockDifference seconds." }

    $awakeResult = [ParameterBaseAwakeState]::SetThreadExecutionState($esContinuous -bor $esSystemRequired)
    if ($awakeResult -eq 0) { throw 'SetThreadExecutionState failed.' }
    'SLEEP_PREVENTION=active_for_this_process'

    & wsl.exe -d Ubuntu-24.04 -- bash $runScript
    $runExit = $LASTEXITCODE
}
finally {
    [void][ParameterBaseAwakeState]::SetThreadExecutionState($esContinuous)
    'SLEEP_PREVENTION=released'
}

exit $runExit
