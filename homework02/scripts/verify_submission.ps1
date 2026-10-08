$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$resultRoot = Join-Path $projectRoot 'specjvm2008\results'

& (Join-Path $PSScriptRoot 'verify_goal1.ps1')
Write-Output 'PASS [01,03-06,15]: homework02 branch; formal .007 raw/TXT, compliance, Composite, historical hashes'

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
    'audit\final_report_evidence_map.md',
    'audit\final_review.md',
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
Write-Output 'PASS [02,08,11]: main Markdown report, SPEC chart, official comparison and supporting artifacts exist'

$report = Get-Content -LiteralPath (Join-Path $projectRoot 'README.md') -Raw
$expectedSections = 1..7  # Match the instructor's seven questions.
foreach ($section in $expectedSections) {
    if ($report -notmatch "(?m)^## $section\.") { throw "Report section missing: $section" }
}
$expectedWorkloads = [ordered]@{
    'compress' = '551.55'
    'derby' = '820.63'
    'sunflow' = '350.25'
    'crypto.aes' = '206.89'
    'scimark.fft.small' = '709.00'
    'scimark.fft.large' = '100.11'
}
$measurements = @{}
foreach ($row in @(Import-Csv -LiteralPath (Join-Path $projectRoot 'analysis\workload_measurements.csv'))) {
    $measurements[$row.workload] = $row.measured_ops_per_min
}
foreach ($name in $expectedWorkloads.Keys) {
    $expectedScore = $expectedWorkloads[$name]
    if ($measurements[$name] -ne $expectedScore) { throw "Unexpected workload score: $name" }
    $rowPrefix = '| ' + [char]96 + $name + [char]96 + ' |'
    $matchingRows = @($report -split "`n" | Where-Object { $_.StartsWith($rowPrefix) -and $_.Contains('**' + $expectedScore + '**') })
    if ($matchingRows.Count -ne 1) { throw "README workload row is missing or ambiguous: $name $expectedScore" }
}
Write-Output 'PASS [07]: six expected workload scores match the analysis table and README'

$repeatRows = @(Import-Csv -LiteralPath (Join-Path $projectRoot 'analysis\repeat_test_results.csv'))
$expectedRepeats = @(
    @{ Run = 'Run1'; ID = 'SPECjvm2008.008'; Score = '557.34' },
    @{ Run = 'Run2'; ID = 'SPECjvm2008.009'; Score = '545.48' },
    @{ Run = 'Run3'; ID = 'SPECjvm2008.010'; Score = '522.15' }
)
if ($repeatRows.Count -ne 3) { throw "Expected exactly 3 original repeat rows, found $($repeatRows.Count)" }
for ($index = 0; $index -lt 3; $index++) {
    $actual = $repeatRows[$index]
    $expected = $expectedRepeats[$index]
    if ($actual.run -ne $expected.Run -or $actual.result_id -ne $expected.ID -or
        $actual.score_ops_per_min -ne $expected.Score) {
        throw "Original repeat row mismatch at index $index"
    }
    foreach ($extension in @('raw', 'txt')) {
        $source = Join-Path $resultRoot "$($expected.ID)\$($expected.ID).$extension"
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing repeat $extension result: $source" }
    }
}
Write-Output 'PASS [09-10]: exactly three original compress repeats, fixed IDs/scores, raw/TXT files present'

$chart = Join-Path $projectRoot 'images\base_scores.jpg'
$sourceChart = Join-Path $resultRoot 'SPECjvm2008.007\images\all.jpg'
$chartHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $chart).Hash
$sourceChartHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceChart).Hash
if ($chartHash -ne $sourceChartHash) { throw 'Report chart differs from the SPEC .007 chart.' }

$markdownFiles = @(Get-ChildItem -LiteralPath $projectRoot -Filter '*.md' -File -Recurse)
$linkCount = 0
$imageCount = 0
$projectFullPath = [IO.Path]::GetFullPath($projectRoot).TrimEnd('\', '/')
foreach ($markdown in $markdownFiles) {
    $body = Get-Content -LiteralPath $markdown.FullName -Raw
    foreach ($match in [regex]::Matches($body, '!?(?<!\\)\[[^\]]+\]\(([^)]+)\)')) {
        $target = $match.Groups[1].Value.Trim('<', '>')
        if ($target -match '^(https?://|mailto:|data:|#)') { continue }
        $target = [Uri]::UnescapeDataString((($target -split '#', 2)[0] -split '\?', 2)[0])
        $resolved = [IO.Path]::GetFullPath((Join-Path $markdown.DirectoryName $target))
        if ($resolved -ine $projectFullPath -and
            -not $resolved.StartsWith($projectFullPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Markdown path escapes the submission directory: $($markdown.FullName): $target"
        }
        if (-not (Test-Path -LiteralPath $resolved)) {
            throw "Broken link in $($markdown.FullName): $target"
        }
        if ($match.Value.StartsWith('!')) {
            if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Image link is not a file: $target" }
            $imageCount++
        }
        $linkCount++
    }
}
$plots = @('base_group_scores.png', 'warmup_measured.png', 'official_comparison.png', 'repeat_compress.png')
foreach ($name in $plots) {
    $reference = '](images/analysis/' + $name + ')'
    if (-not $report.Contains($reference)) { throw "README does not embed the analysis plot: $name" }
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ('images\analysis\' + $name)) -PathType Leaf)) {
        throw "Missing analysis plot: $name"
    }
}
Write-Output "PASS [12-14]: $linkCount local Markdown links resolve within submission; $imageCount image links; four analysis plots embedded"

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
Write-Output 'PASS [05-07,10]: formal and repeat raw/TXT agree with derived scores and CSVs'
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

Write-Output 'PASS [08,11,13,15]: SPEC graph, official snapshots, derived plots and source-hash manifest verified'
Write-Output 'Submission verification: PASS (15 required conditions; Markdown report, no PDF required)'
