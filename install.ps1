[CmdletBinding()]
param(
  [ValidateSet('User','Project')][string]$Scope = 'User',
  [string]$ProjectRoot = '.',
  [ValidateSet('All','Codex','Claude','WorkBuddy','Gemini','OpenCode')][string]$Agent = 'All',
  [string]$TargetDir = '',
  [switch]$InstallMcp,
  [switch]$Force,
  [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
Get-Command python -ErrorAction Stop | Out-Null
$argsList = @('-X', 'utf8', (Join-Path $PSScriptRoot 'scripts\install_skill.py'), '--agent', $Agent.ToLowerInvariant(), '--scope', $Scope.ToLowerInvariant(), '--project-root', $ProjectRoot)
if ($TargetDir) { $argsList += @('--target-dir', $TargetDir) }
if ($Force) { $argsList += '--force' }
if ($DryRun) { $argsList += '--dry-run' }
& python @argsList
if ($LASTEXITCODE -ne 0) { throw 'Skill install failed' }
if ($InstallMcp -and -not $DryRun) {
  & python -X utf8 (Join-Path $PSScriptRoot 'scripts\configure_mcp.py') --agent $Agent.ToLowerInvariant() --scope $Scope.ToLowerInvariant() --project-root $ProjectRoot --apply
  if ($LASTEXITCODE -ne 0) { throw 'Skill installed, but MCP setup failed' }
}
Write-Host 'Installed Agent Skill. In Codex use $sci-literature; in Claude Code use /sci-literature.' -ForegroundColor Cyan
