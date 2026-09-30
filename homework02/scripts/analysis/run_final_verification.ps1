$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$log = Join-Path $projectRoot 'logs\final_core_verification.log'
$lines = [Collections.Generic.List[string]]::new()
$lines.Add("PURPOSE=Final A2 core read-only verification")
$lines.Add("START_TIME=$((Get-Date).ToString('o'))")
$lines.Add("PROJECT_ROOT=$projectRoot")
[IO.File]::WriteAllText($log, (($lines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))

try {
    # Exercise the old fail-open case without changing Git state or source files.
    $missingGitDir = Join-Path (Split-Path -Parent $projectRoot) '__a2_nonexistent_git_dir_for_negative_test__'
    if (Test-Path -LiteralPath $missingGitDir) { throw 'Negative-test Git path unexpectedly exists.' }
    $previousGitDir = $env:GIT_DIR
    try {
        $env:GIT_DIR = $missingGitDir
        $negativeRejected = $false
        try {
            & (Join-Path (Split-Path -Parent $PSScriptRoot) 'verify_goal1.ps1') | Out-Null
        }
        catch {
            if ($_.Exception.Message -notmatch 'Git repository not available') { throw }
            $negativeRejected = $true
            $lines.Add("NEGATIVE_NO_GIT=EXPECTED_FAIL: $($_.Exception.Message)")
        }
        if (-not $negativeRejected) { throw 'Verifier was fail-open outside a Git repository.' }
    }
    finally {
        if ($null -eq $previousGitDir) { Remove-Item Env:\GIT_DIR -ErrorAction SilentlyContinue }
        else { $env:GIT_DIR = $previousGitDir }
    }
    foreach ($scriptName in @('verify_goal1.ps1', 'verify_submission.ps1')) {
        $script = Join-Path (Split-Path -Parent $PSScriptRoot) $scriptName
        $lines.Add("COMMAND=pwsh -NoProfile -File $script")
        foreach ($item in @(& $script)) { $lines.Add([string]$item) }
    }
    $lines.Add("END_TIME=$((Get-Date).ToString('o'))")
    $lines.Add('VERIFICATION_STATUS=PASS')
}
catch {
    $lines.Add("ERROR=$($_.Exception.Message)")
    $lines.Add("END_TIME=$((Get-Date).ToString('o'))")
    $lines.Add('VERIFICATION_STATUS=FAIL')
    throw
}
finally {
    [IO.File]::WriteAllText($log, (($lines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))
}
$lines
