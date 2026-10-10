param(
    [Parameter(Mandatory=$true)][string]$EvidenceDirectory,
    [Parameter(Mandatory=$true)][string]$PythonExecutable,
    [ValidateSet('recover','resume','check')][string]$Mode = 'resume',
    [string]$RecoveryDirectory = '',
    [string]$AuxiliarySha = '',
    [string]$ProbeFile = '',
    [string]$ContentSha = '',
    [string]$ArchiveDirectory = '',
    [string]$CampaignDirectory = '',
    [string]$GitIdentity = '',
    [string]$SessionId = '',
    [int]$Intervals = 10
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Always launched by start_p3_first_seed.py with a child-only PSModulePath.
$hashCommand = Get-Command Get-FileHash -ErrorAction Stop
$scriptPath = Join-Path $PSScriptRoot 'start_p3_first_seed.py'
$startup = [ordered]@{schema='p3-windows-startup-v2'; pid=$PID;
    powershell_executable=(Get-Process -Id $PID).Path; powershell_version=$PSVersionTable.PSVersion.ToString();
    get_file_hash_source=$hashCommand.Source;
    controller_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower();
    python_launcher_sha256=(Get-FileHash -LiteralPath $scriptPath -Algorithm SHA256).Hash.ToLower()}
[IO.File]::WriteAllText((Join-Path $EvidenceDirectory 'windows_startup.json'),
    ($startup | ConvertTo-Json -Depth 5).Replace([Environment]::NewLine,[string][char]10) + [char]10,
    [Text.UTF8Encoding]::new($false))
$arguments = @($scriptPath,'--child','--output',$EvidenceDirectory,'--mode',$Mode,'--intervals',[string]$Intervals)
if ($RecoveryDirectory) { $arguments += @('--recovery-directory',$RecoveryDirectory) }
if ($AuxiliarySha) { $arguments += @('--auxiliary-sha',$AuxiliarySha) }
if ($ProbeFile) { $arguments += @('--probe-file',$ProbeFile) }
if ($ContentSha) { $arguments += @('--content-sha',$ContentSha) }
if ($ArchiveDirectory) { $arguments += @('--archive-directory',$ArchiveDirectory) }
if ($CampaignDirectory) { $arguments += @('--campaign-directory',$CampaignDirectory) }
if ($GitIdentity) { $arguments += @('--git-identity',$GitIdentity) }
if ($SessionId) { $arguments += @('--session-id',$SessionId) }
& $PythonExecutable @arguments
if ($null -eq $LASTEXITCODE) { throw 'Python child exit code unknown' }
exit $LASTEXITCODE
