$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$resultRoot = Join-Path $projectRoot 'specjvm2008\results'

& (Join-Path $PSScriptRoot 'verify_goal1.ps1')

$required = @(
    'README.md',
    'images\base_scores.jpg',
    'analysis\specjvm_background.md',
    'analysis\workload_analysis.md',
    'analysis\official_comparison.md',
    'analysis\repeat_test_results.csv',
    'analysis\repeat_test_analysis.md',
    'analysis\jvm_parameter_base_results.csv',
    'analysis\jvm_parameter_experiment.md'
)
foreach ($relative in $required) {
    $file = Join-Path $projectRoot $relative
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Missing submission file: $relative"
    }
}
if (Test-Path -LiteralPath (Join-Path $projectRoot 'report.md')) {
    throw 'A second top-level report.md exists.'
}

$chart = Join-Path $projectRoot 'images\base_scores.jpg'
$sourceChart = Join-Path $resultRoot 'SPECjvm2008.007\images\all.jpg'
$chartHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $chart).Hash
$sourceChartHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceChart).Hash
if ($chartHash -ne $sourceChartHash) { throw 'Report chart differs from the SPEC .007 chart.' }

$markdownFiles = @((Get-Item -LiteralPath (Join-Path $projectRoot 'README.md')))
$markdownFiles += Get-ChildItem -LiteralPath (Join-Path $projectRoot 'analysis') -Filter '*.md' -File
$linkCount = 0
foreach ($markdown in $markdownFiles) {
    $body = Get-Content -LiteralPath $markdown.FullName -Raw
    foreach ($match in [regex]::Matches($body, '!?(?<!\\)\[[^\]]+\]\(([^)]+)\)')) {
        $target = $match.Groups[1].Value
        if ($target -match '^(https?://|mailto:|#)') { continue }
        $target = ($target -split '#', 2)[0]
        $resolved = [IO.Path]::GetFullPath((Join-Path $markdown.DirectoryName $target))
        if (-not (Test-Path -LiteralPath $resolved)) {
            throw "Broken link in $($markdown.FullName): $target"
        }
        $linkCount++
    }
}

$datasets = @(
    @{ File = 'analysis\repeat_test_results.csv'; Expected = 3 },
    @{ File = 'analysis\jvm_parameter_base_results.csv'; Expected = 2 }
)
foreach ($dataset in $datasets) {
    $rows = @(Import-Csv -LiteralPath (Join-Path $projectRoot $dataset.File))
    if ($rows.Count -ne $dataset.Expected) { throw "Wrong row count in $($dataset.File)." }
    foreach ($row in $rows) {
        $id = $row.result_id
        $raw = Join-Path $resultRoot "$id\$id.raw"
        $txt = Join-Path $resultRoot "$id\$id.txt"
        if (-not (Test-Path -LiteralPath $raw -PathType Leaf)) { throw "Missing raw: $id" }
        if (-not (Test-Path -LiteralPath $txt -PathType Leaf)) { throw "Missing text report: $id" }
        $score = [regex]::Escape($row.score_ops_per_min)
        if (-not (Select-String -LiteralPath $txt -Pattern "^compress\s+$score\s*$" -Quiet)) {
            throw "CSV score does not match SPEC text report: $id"
        }
        if (-not (Select-String -LiteralPath $txt -Pattern '^Run is valid, but not compliant$' -Quiet)) {
            throw "Unexpected single-workload validity status: $id"
        }
    }
}

$repositoryRoot = Split-Path -Parent $projectRoot
& git -C $repositoryRoot rev-parse --is-inside-work-tree 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $branch = (& git -C $repositoryRoot branch --show-current).Trim()
    if ($branch -ne 'homework02') { throw "Wrong Git branch: $branch" }
    Write-Output "Git branch: $branch"
}

Write-Output "Submission verification: PASS; relative Markdown links: $linkCount; repeat rows: 3; parameter rows: 2"
