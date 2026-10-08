param([string]$ContentSha = '')
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot
if (-not $ContentSha) { $ContentSha = (git rev-parse HEAD).Trim() }
if ($ContentSha -notmatch '^[0-9a-f]{40}$') { throw 'Expected a full content commit SHA' }
$destination = Join-Path $repoRoot 'build/p2'
New-Item -ItemType Directory -Force $destination | Out-Null
$archive = Join-Path $destination ($ContentSha + '.tar')
git archive --format=tar -o $archive $ContentSha
if ($LASTEXITCODE -ne 0) { throw 'git archive failed' }
$files = [ordered]@{}
foreach ($line in (git ls-tree -r $ContentSha)) {
    if ($line -match '^100\d+ blob ([0-9a-f]{40})\t(.+)$') {
        $relative = $matches[2]
        $blobSha = $matches[1]
        if ($relative -match '^(autotuner/.*\.py|code/(working|original)/.*\.[ch]|configs/.*\.json|scripts/(check_p2_resources\.ps1|run_p[23]_.*\.py|audit_p[23]_evidence\.py)|\.gitattributes)$') {
            $files[$relative] = $blobSha
        }
    }
}
if (-not $files.Contains('autotuner/core.py') -or -not $files.Contains('autotuner/session.py')) { throw 'Required Python modules missing from commit' }
$identity = [ordered]@{content_sha=$ContentSha; files=$files}
$identityPath = Join-Path $destination 'git_identity.json'
[IO.File]::WriteAllText($identityPath, ($identity | ConvertTo-Json -Depth 5) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
$executionRoot = '/var/tmp/matrix-autotuner-p2-content-' + $ContentSha
$archiveNormalized = $archive.Replace('\', '/')
$archiveWsl = (wsl.exe -d Ubuntu-24.04 -- wslpath -u $archiveNormalized).Trim()
wsl.exe -d Ubuntu-24.04 -- mkdir -p $executionRoot
wsl.exe -d Ubuntu-24.04 -- tar -xf $archiveWsl -C $executionRoot
if ($LASTEXITCODE -ne 0) { throw 'content extraction failed' }
[ordered]@{content_sha=$ContentSha; execution_root=$executionRoot; git_identity=$identityPath} | ConvertTo-Json
