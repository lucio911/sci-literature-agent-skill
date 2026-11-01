[CmdletBinding()]
param(
    [ValidateSet('User', 'Project')][string]$Scope = 'User',
    [string]$ProjectRoot = '.',
    [switch]$InstallMcp,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'skill'
if (-not (Test-Path (Join-Path $source 'SKILL.md'))) { throw 'Skill directory missing; extract ZIP first.' }
if ($Scope -eq 'User') {
    $target = Join-Path $HOME '.agents\skills\sci-literature'
} else {
    $project = (Resolve-Path -LiteralPath $ProjectRoot).Path
    $target = Join-Path $project '.agents\skills\sci-literature'
}
if ((Test-Path $target) -and -not $Force) {
    throw "Target exists: $target (use -Force to replace that skill folder)"
}
if (Test-Path $target) { Remove-Item -LiteralPath $target -Force -Recurse }
New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $target -Recurse -Force
Write-Host "Installed skill: $target" -ForegroundColor Green
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) { Write-Warning 'Python 3.10+ not found. Install Python and confirm python --version.' }
else {
    & python -X utf8 (Join-Path $target 'scripts\sci_refs.py') --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Python runtime test failed.' }
    Write-Host 'Python script accessible.'
}
if ($InstallMcp) {
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) { throw 'Codex CLI not found: install Codex before -InstallMcp.' }
    if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) { throw 'uvx not found: install uv and reopen terminal before -InstallMcp.' }
    $mcpList = (& codex mcp list 2>&1 | Out-String)
    if ($mcpList -match '(?m)^\s*paper-search\s') {
        Write-Host 'paper-search MCP already appears in codex mcp list; no change.'
    } else {
        & codex mcp add paper-search -- uvx paper-search-mcp
        if ($LASTEXITCODE -ne 0) { throw 'codex mcp add failed; inspect your Codex configuration.' }
    }
    & codex mcp list
}
Write-Host 'Restart Codex if the skill is not discovered. Invoke: $sci-literature' -ForegroundColor Cyan
