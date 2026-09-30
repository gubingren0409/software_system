$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
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
    (Join-Path $resultRoot 'images\all.jpg')
)

foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing required artifact: $path"
    }
}

$scoreCount = (Select-String -LiteralPath $baseLog -Pattern '^Score on ').Count
$validCount = (Select-String -LiteralPath $baseLog -Pattern '^Valid run!$').Count
$invalidCount = (Select-String -LiteralPath $baseLog -Pattern 'NOT VALID').Count
$oomCount = (Select-String -LiteralPath $baseLog -Pattern 'OutOfMemoryError').Count
$composite = Select-String -LiteralPath $baseLog -Pattern '^Composite result: 421\.24 SPECjvm2008 Base ops/m$'
$exitStatus = Select-String -LiteralPath $baseLog -Pattern '^EXIT_STATUS=0$'
$compliant = Select-String -LiteralPath $textReport -Pattern '^Run is compliant$'
$rawHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $rawFile).Hash.ToLowerInvariant()
$expectedRawHash = '4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad'

if ($scoreCount -ne 38) { throw "Expected 38 workload scores, found $scoreCount." }
if ($validCount -ne 39) { throw "Expected 39 valid runs including the check, found $validCount." }
if ($invalidCount -ne 0) { throw "Found $invalidCount NOT VALID marker(s)." }
if ($oomCount -ne 0) { throw "Found $oomCount OutOfMemoryError marker(s)." }
if (-not $composite) { throw 'Expected Base composite result was not found.' }
if (-not $exitStatus) { throw 'Successful benchmark exit status was not found.' }
if (-not $compliant) { throw 'The generated SPEC text report does not mark the run compliant.' }
if ($rawHash -ne $expectedRawHash) { throw "Raw result hash mismatch: $rawHash" }

Write-Output 'Goal 1 verification: PASS'
Write-Output "Workload scores: $scoreCount"
Write-Output "Valid runs (including check): $validCount"
Write-Output 'Composite: 421.24 SPECjvm2008 Base ops/m'
Write-Output 'SPEC report: Run is compliant'
Write-Output "Raw SHA-256: $rawHash"
