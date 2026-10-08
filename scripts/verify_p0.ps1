$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$expectedSourceHash = '188D011109C4470E1F41829216E8677A5C2D8F2B7C8A44215652320DBDF6DE15'
$actualSourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'code/original/matrix_multiplication.c').Hash
if ($actualSourceHash -ne $expectedSourceHash) {
    throw "Original source hash mismatch: $actualSourceHash"
}

$requiredFiles = @(
    'README.md',
    'report.md',
    'docs/P0_DISCOVERY.md',
    'docs/WORK_LOG.md',
    'docs/AUDIT_HANDOFF.md',
    'evidence/p0/environment_host.txt',
    'evidence/p0/environment_wsl.txt',
    'evidence/p0/preexperiment/summary.csv',
    'evidence/p0/preexperiment/compile_original_O1.txt',
    'evidence/p0/preexperiment/compile_original_O2.txt',
    'evidence/p0/preexperiment/valgrind_n65_s24.command.txt',
    'evidence/p0/preexperiment/valgrind_n65_s24.stderr.txt'
)
foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing required file: $path"
    }
}

$rows = Import-Csv -LiteralPath 'evidence/p0/preexperiment/summary.csv'
$valid = @($rows | Where-Object { [int]$_.block_size -le [int]$_.matrix_n })
$rejected = @($rows | Where-Object { [int]$_.block_size -gt [int]$_.matrix_n })
if ($valid.Count -ne 6 -or @($valid | Where-Object { $_.exit_code -ne '0' -or $_.verification -ne 'PASS' }).Count -ne 0) {
    throw 'Preexperiment valid-case verification failed.'
}
if ($rejected.Count -ne 2 -or @($rejected | Where-Object { $_.exit_code -eq '0' }).Count -ne 0) {
    throw 'Preexperiment expected-rejection verification failed.'
}

$valgrindCommand = Get-Content -LiteralPath 'evidence/p0/preexperiment/valgrind_n65_s24.command.txt' -Raw
$valgrindLog = Get-Content -LiteralPath 'evidence/p0/preexperiment/valgrind_n65_s24.stderr.txt' -Raw
if ($valgrindCommand -notmatch 'exit_code=0' -or $valgrindLog -notmatch 'ERROR SUMMARY: 0 errors') {
    throw 'Valgrind evidence verification failed.'
}

$trackedLargeFiles = git ls-files | ForEach-Object {
    $item = Get-Item -LiteralPath $_
    if ($item.Length -gt 5MB) { $item }
}
if ($trackedLargeFiles) {
    throw "Unexpected tracked files larger than 5 MiB: $($trackedLargeFiles.FullName -join ', ')"
}

Write-Output "source_hash=$actualSourceHash"
Write-Output "valid_cases=$($valid.Count)"
Write-Output "expected_rejections=$($rejected.Count)"
Write-Output 'valgrind_errors=0'
Write-Output 'p0_verification=PASS'
