$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$resultRoot = Join-Path $projectRoot 'specjvm2008\results'

& (Join-Path $PSScriptRoot 'verify_goal1.ps1')

# Goal-specific handoff artifacts. This is not a claim that the instructor
# requires every format listed here (in particular, no PDF is mandatory).
$required = @(
    'README.md',
    'images\base_scores.jpg',
    'analysis\specjvm_background.md',
    'analysis\environment_summary.md',
    'analysis\workload_analysis.md',
    'analysis\base_result_table.csv',
    'analysis\workload_measurements.csv',
    'analysis\official_comparison.md',
    'analysis\official_reference_candidates.csv',
    'analysis\official_group_scores.csv',
    'analysis\official_reference_huawei.html',
    'analysis\repeat_test_results.csv',
    'analysis\repeat_statistics.csv',
    'analysis\repeat_test_analysis.md',
    'analysis\diagnostics\profile_analysis.md',
    'analysis\diagnostics\profile_summary.csv',
    'audit\core_evidence_audit.md',
    'audit\evidence_manifest.csv',
    'audit\remaining_risks.md',
    'audit\self_review.md',
    'environment\final_repository_state.txt',
    'scripts\analysis\build_core_data.py',
    'scripts\analysis\build_evidence_manifest.py',
    'scripts\analysis\verify_official_data.py',
    'scripts\analysis\verify_document_tables.py',
    'scripts\analysis\build_profile_summary.py',
    'scripts\analysis\run_diagnostic_profiles.sh',
    'scripts\analysis\collect_telemetry_feasibility.ps1',
    'scripts\analysis\plot_core.py',
    'images\analysis\base_group_scores.png',
    'images\analysis\warmup_measured.png',
    'images\analysis\repeat_compress.png',
    'images\analysis\official_comparison.png',
    'logs\diagnostics\profile_compress_015.log',
    'logs\diagnostics\profile_sunflow_016.log',
    'logs\diagnostics\telemetry_feasibility.log',
    'specjvm2008\results\SPECjvm2008.015\SPECjvm2008.015.raw',
    'specjvm2008\results\SPECjvm2008.016\SPECjvm2008.016.raw'
)
foreach ($relative in $required) {
    $file = Join-Path $projectRoot $relative
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Missing submission file: $relative"
    }
}
$chart = Join-Path $projectRoot 'images\base_scores.jpg'
$sourceChart = Join-Path $resultRoot 'SPECjvm2008.007\images\all.jpg'
$chartHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $chart).Hash
$sourceChartHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceChart).Hash
if ($chartHash -ne $sourceChartHash) { throw 'Report chart differs from the SPEC .007 chart.' }

$markdownFiles = @((Get-Item -LiteralPath (Join-Path $projectRoot 'README.md')))
$markdownFiles += Get-ChildItem -LiteralPath (Join-Path $projectRoot 'analysis') -Filter '*.md' -File -Recurse
$markdownFiles += Get-ChildItem -LiteralPath (Join-Path $projectRoot 'audit') -Filter '*.md' -File
$markdownFiles += Get-ChildItem -LiteralPath (Join-Path $projectRoot 'scripts\analysis') -Filter '*.md' -File
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

$tables = @(
    @{ File = 'analysis\base_result_table.csv'; Expected = 12 },
    @{ File = 'analysis\workload_measurements.csv'; Expected = 38 },
    @{ File = 'analysis\repeat_test_results.csv'; Expected = 3 },
    @{ File = 'analysis\repeat_statistics.csv'; Expected = 3 },
    @{ File = 'analysis\official_reference_candidates.csv'; Expected = 6 },
    @{ File = 'analysis\official_group_scores.csv'; Expected = 14 },
    @{ File = 'analysis\diagnostics\profile_summary.csv'; Expected = 2 }
)
foreach ($table in $tables) {
    $rows = @(Import-Csv -LiteralPath (Join-Path $projectRoot $table.File))
    if ($rows.Count -ne $table.Expected) { throw "Wrong row count in $($table.File): $($rows.Count)" }
}

& python (Join-Path $PSScriptRoot 'analysis\build_core_data.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Core CSVs disagree with raw results.' }
& python (Join-Path $PSScriptRoot 'analysis\build_evidence_manifest.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Evidence manifest disagrees with source files.' }
& python (Join-Path $PSScriptRoot 'analysis\verify_official_data.py')
if ($LASTEXITCODE -ne 0) { throw 'Selected official data disagree with saved SPEC reports.' }
& python (Join-Path $PSScriptRoot 'analysis\verify_document_tables.py')
if ($LASTEXITCODE -ne 0) { throw 'Markdown analysis tables disagree with source CSVs.' }
& python (Join-Path $PSScriptRoot 'analysis\build_profile_summary.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic summary disagrees with independent raw/log evidence.' }
& python (Join-Path $PSScriptRoot 'analysis\plot_core.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Core figures disagree with source tables.' }

Write-Output "Submission verification: PASS; relative Markdown links: $linkCount; core CSVs and figures checked"
