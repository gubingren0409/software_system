$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$baseLog = Join-Path $projectRoot 'logs\base_run.log'
$resultRoot = Join-Path $projectRoot 'specjvm2008\results\SPECjvm2008.007'
$rawFile = Join-Path $resultRoot 'SPECjvm2008.007.raw'
$textReport = Join-Path $resultRoot 'SPECjvm2008.007.txt'
$requiredFiles = @(
    $baseLog,
    (Join-Path $projectRoot 'environment\environment_info.txt'),
    (Join-Path $projectRoot 'logs\reporter_regeneration.log'),
    $rawFile,
    $textReport,
    (Join-Path $resultRoot 'SPECjvm2008.007.html'),
    (Join-Path $resultRoot 'SPECjvm2008.007.summary'),
    (Join-Path $resultRoot 'SPECjvm2008.007.sub'),
    (Join-Path $resultRoot 'images\all.jpg')
)

foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing required artifact: $path"
    }
}

$gitRoot = & git -C $repositoryRoot rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0 -or -not $gitRoot) { throw 'Git repository not available.' }
$expectedRoot = [IO.Path]::GetFullPath($repositoryRoot).TrimEnd('\', '/')
$actualRoot = [IO.Path]::GetFullPath($gitRoot.Trim()).TrimEnd('\', '/')
if ($actualRoot -ine $expectedRoot) { throw "Wrong Git repository: $actualRoot" }
$branch = & git -C $repositoryRoot branch --show-current 2>$null
if ($LASTEXITCODE -ne 0 -or $branch.Trim() -ne 'homework02') {
    throw "Expected branch homework02, found: $branch"
}

$scoreCount = (Select-String -LiteralPath $baseLog -Pattern '^Score on ').Count
$validCount = (Select-String -LiteralPath $baseLog -Pattern '^Valid run!$').Count
$invalidCount = (Select-String -LiteralPath $baseLog -Pattern 'NOT VALID').Count
$oomCount = (Select-String -LiteralPath $baseLog -Pattern 'OutOfMemoryError').Count
$composite = Select-String -LiteralPath $baseLog -Pattern '^Composite result: 421\.24 SPECjvm2008 Base ops/m$'
$exitStatus = Select-String -LiteralPath $baseLog -Pattern '^EXIT_STATUS=0$'
$compliant = Select-String -LiteralPath $textReport -Pattern '^Run is compliant$'
$reportComposite = Select-String -LiteralPath $textReport -Pattern '^Composite result: 421\.24 SPECjvm2008 Base ops/m$'
$reportThreads = Select-String -LiteralPath $textReport -Pattern '^specjvm\.benchmark\.threads=16$'
$reportVersion = Select-String -LiteralPath $textReport -Pattern 'SPECjvm2008 Version: \[SPECjvm2008 1\.01'
$html = Get-Content -LiteralPath (Join-Path $resultRoot 'SPECjvm2008.007.html') -Raw
$summary = Get-Content -LiteralPath (Join-Path $resultRoot 'SPECjvm2008.007.summary') -Raw
$submission = Get-Content -LiteralPath (Join-Path $resultRoot 'SPECjvm2008.007.sub') -Raw
$reporterLog = Get-Content -LiteralPath (Join-Path $projectRoot 'logs\reporter_regeneration.log') -Raw
$rawHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $rawFile).Hash.ToLowerInvariant()
$expectedRawHash = '4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad'

if ($scoreCount -ne 38) { throw "Expected 38 workload scores, found $scoreCount." }
if ($validCount -ne 39) { throw "Expected 39 valid runs including the check, found $validCount." }
if ($invalidCount -ne 0) { throw "Found $invalidCount NOT VALID marker(s)." }
if ($oomCount -ne 0) { throw "Found $oomCount OutOfMemoryError marker(s)." }
if (-not $composite) { throw 'Expected Base composite result was not found.' }
if (-not $exitStatus) { throw 'Successful benchmark exit status was not found.' }
if (-not $compliant) { throw 'The generated SPEC text report does not mark the run compliant.' }
if (-not $reportComposite -or -not $reportThreads -or -not $reportVersion) {
    throw 'SPEC text report score, thread count, or version is inconsistent.'
}
if ($html -notmatch 'Run is compliant' -or $html -notmatch 'Composite result: 421\.24 SPECjvm2008 Base ops/m') {
    throw 'SPEC HTML report is inconsistent.'
}
if ($summary -notmatch 'Composite result: 421\.24 SPECjvm2008 Base ops/m') {
    throw 'SPEC summary is inconsistent.'
}
if ($submission -notmatch 'spec\.jvm2008\.report\.result\.status=Run is compliant' -or
    $submission -notmatch 'spec\.jvm2008\.report\.result\.score=421\.24') {
    throw 'SPEC submission metadata is inconsistent.'
}
if ($reporterLog -notmatch '\-\-reporter .*SPECjvm2008\.007\.raw' -or $reporterLog -notmatch 'EXIT_STATUS=0') {
    throw 'Separate reporter invocation is not verified.'
}
if ($rawHash -ne $expectedRawHash) { throw "Raw result hash mismatch: $rawHash" }

$historicPaths = @(
    'logs/base_run.log',
    'logs/reporter_regeneration.log',
    'environment/environment_info.txt',
    'specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw',
    'specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt',
    'specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.html'
)
$historicHashes = @{}
foreach ($line in Get-Content -LiteralPath (Join-Path $projectRoot 'environment\artifact_sha256.txt')) {
    if ($line -match '^([0-9a-f]{64})\s+(.+)$') {
        $historicHashes[$Matches[2]] = $Matches[1]
    }
}
foreach ($relative in $historicPaths) {
    if (-not $historicHashes.ContainsKey($relative)) { throw "Historical SHA-256 missing: $relative" }
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $projectRoot $relative)).Hash.ToLowerInvariant()
    if ($actualHash -ne $historicHashes[$relative]) { throw "Historical SHA-256 mismatch: $relative" }
}

Write-Output 'Goal 1 verification: PASS'
Write-Output "Workload scores: $scoreCount"
Write-Output "Valid runs (including check): $validCount"
Write-Output 'Composite: 421.24 SPECjvm2008 Base ops/m'
Write-Output 'SPEC report: Run is compliant'
Write-Output "Git branch: $branch"
Write-Output "Raw SHA-256: $rawHash"
Write-Output "Historical core hashes verified: $($historicPaths.Count)"
