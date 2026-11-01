[CmdletBinding()]
param(
  [string]$Repo = 'lucio911/sci-literature-codex',
  [ValidateSet('public', 'private')][string]$Visibility = 'public'
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
foreach ($name in @('git', 'gh')) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "$name is required. Install Git for Windows and GitHub CLI, then sign in with: gh auth login"
  }
}
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI is not authenticated. Run: gh auth login' }
if (-not (Test-Path .git)) {
  & git init -b main
  if ($LASTEXITCODE -ne 0) { throw 'git init failed' }
}
& git add README.md AGENTS.snippet.md .gitignore LICENSE install.ps1 publish.ps1 .github docs examples skill tests
if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  & git commit -m 'Initial release: SCI literature Codex Skill for LaTeX'
  if ($LASTEXITCODE -ne 0) { throw 'Commit failed; configure your git user.name and user.email' }
}
& gh repo view $Repo --json nameWithOwner 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
  & gh repo create $Repo "--$Visibility" --source . --remote origin --push
  if ($LASTEXITCODE -ne 0) { throw 'GitHub repository creation or push failed.' }
} else {
  & git remote get-url origin 1>$null 2>$null
  if ($LASTEXITCODE -ne 0) { & git remote add origin "https://github.com/$Repo.git" }
  $upstream = (& git remote get-url origin)
  if ($upstream -notmatch [regex]::Escape($Repo)) { throw "Origin points to another repository: $upstream" }
  & git push -u origin main
  if ($LASTEXITCODE -ne 0) { throw 'Push failed; inspect branch history and permissions.' }
}
Write-Host "Repository: https://github.com/$Repo" -ForegroundColor Green
