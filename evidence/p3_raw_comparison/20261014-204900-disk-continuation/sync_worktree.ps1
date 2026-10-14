$ErrorActionPreference = 'Stop'
$repo = 'E:\software_system\project01'
$source = Join-Path $repo 'evidence\p3_raw_comparison\20261014-182807-ac-validation'
$rescue = 'C:\Users\28489\AppData\Local\Temp\matrix-validation-rescue-20261014-184709'
$committed = Join-Path $rescue 'repository\evidence\p3_raw_comparison\20261014-182807-ac-validation'
$backup = Join-Path $rescue 'original-e-pre-sync-20261014-204900'
$out = $PSScriptRoot
Start-Transcript -LiteralPath (Join-Path $out 'sync.transcript.txt') -NoClobber
try {
    Get-Date -Format o
    Set-Location -LiteralPath $repo
    git status --short --branch
    git remote -v
    git -C (Join-Path $rescue 'repository') rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read rescue repository' }
    $manifest = @()
    foreach ($file in (Get-ChildItem -LiteralPath $source -Recurse -File -Force)) {
        $relative = $file.FullName.Substring($source.Length + 1)
        $other = Join-Path $committed $relative
        if (-not (Test-Path -LiteralPath $other -PathType Leaf)) { throw "Missing committed backup: $relative" }
        $before = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLower()
        $after = (Get-FileHash -LiteralPath $other -Algorithm SHA256).Hash.ToLower()
        if ($before -ne $after -and $relative -ne 'finalize_validation.py') { throw "Unexpected difference: $relative" }
        $manifest += [pscustomobject]@{path=$relative; bytes=$file.Length; original_sha256=$before; committed_sha256=$after}
    }
    $manifest | ConvertTo-Json -Depth 5 | Out-File -LiteralPath (Join-Path $out 'pre_sync_original_files.json') -Encoding utf8
    git fetch (Join-Path $rescue 'repository') project01
    if ($LASTEXITCODE -ne 0) { throw 'Local rescue fetch failed' }
    git merge-base --is-ancestor HEAD FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Refusing non-fast-forward' }
    if ((Resolve-Path -LiteralPath $source).Path -ne $source) { throw 'Source path differs' }
    if ([IO.Path]::GetFullPath($backup) -ne $backup -or -not $backup.StartsWith($rescue + '\') -or (Test-Path -LiteralPath $backup)) { throw 'Unsafe backup destination' }
    Move-Item -LiteralPath $source -Destination $backup
    foreach ($entry in $manifest) {
        if ((Get-FileHash -LiteralPath (Join-Path $backup $entry.path) -Algorithm SHA256).Hash.ToLower() -ne $entry.original_sha256) { throw 'Backup bytes differ' }
    }
    git merge --ff-only FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed; original is preserved in backup' }
    git status --short --branch
    git rev-parse HEAD
    Get-PSDrive E,C | Select-Object Name,Free,Used
    Write-Output "Preserved original E activity at $backup; fast-forwarded without reset or overwriting user modifications."
} finally { Stop-Transcript }
