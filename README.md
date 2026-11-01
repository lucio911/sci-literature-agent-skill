# SCI Literature Assistant for Windows Codex (LaTeX + BibTeX)

A usable, conservative Codex Skill with Python DOI/bibliography helpers and a compatible Paper Search MCP setup. **Not an MCP server itself**: the skill reads MCP search results through Codex and invokes its own scripts for deterministic changes.

## Contents

```text
sci-literature-codex/
├── README.md
├── .github/workflows/ci.yml
├── .gitignore
├── LICENSE
├── publish.ps1
├── docs/QUICKSTART.zh-CN.md
├── install.ps1
├── AGENTS.snippet.md
├── skill/
│   ├── SKILL.md
│   ├── assets/plan.template.json
│   ├── references/QUALITY-GATES.md
│   └── scripts/sci_refs.py
├── examples/plan.template.json
└── tests/test_sci_refs.py
```

[中文快速入门](docs/QUICKSTART.zh-CN.md) · [完整 Skill](skill/SKILL.md) · [引用质量检查](skill/references/QUALITY-GATES.md) · [测试](tests/test_sci_refs.py)

## Prerequisites (Windows)

- Codex CLI (or Codex IDE extension sharing CLI config). Check `codex --version`.
- Python 3.10+ on `PATH`. Check `python --version`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) to run the search MCP. Check `uvx --version`.
- TeX Live / MiKTeX and `latexmk` for local compilation (recommended, not needed for search/import/audit).
- Access to Crossref and academic services. HTTP/Proxy/firewall restrictions can prevent remote requests.

## Publishing your own copy

For the repository owner, the optional `publish.ps1` script can create a standalone GitHub repository and push `main` using the authenticated GitHub CLI (`gh auth login` required). Confirm the destination and visibility before executing. The script does not publish automatically during installation.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\publish.ps1 -Repo lucio911/sci-literature-codex -Visibility public
```

## Installation

1. Extract the release ZIP (do not execute code from an untrusted archive without checking it).
2. Open PowerShell inside the extracted `sci-literature-codex` directory.
3. Install for all projects:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Scope User -InstallMcp
```

Or install into one project without configuring MCP:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Scope Project -ProjectRoot 'D:\papers\shield-tunnel'
```

4. Alternatively configure MCP separately:

```powershell
codex mcp add paper-search -- uvx paper-search-mcp
codex mcp list
```

If a `paper-search` server is already registered, inspect it rather than overwriting it.

**Manual MCP TOML alternative**: Add only this table (do not delete other entries) to `%USERPROFILE%\.codex\config.toml`:

```toml
[mcp_servers.paper-search]
command = "uvx"
args = ["paper-search-mcp"]
startup_timeout_sec = 60
```

Optional API keys are managed by the MCP project in `%USERPROFILE%\.config\paper-search-mcp\.env` (normal `~/.config/paper-search-mcp/.env` layout), not by this repo. See the upstream `.env.example`. No keys are required for basic Crossref search. Avoid committing credentials. If `uvx` executable is not on PATH when Codex launches, supply the full path in TOML.

For `sci_refs.py`'s polite Crossref access, optionally set `CROSSREF_MAILTO` in your user environment to a valid contact email.

5. Restart Codex if necessary, then use `$sci-literature` or `/skills` to invoke the skill.

## Typical commands in the LaTeX repository

Set the script location once (user-global installation):

```powershell
$skillScript = Join-Path $HOME '.agents\skills\sci-literature\scripts\sci_refs.py'
cd 'D:\papers\shield-tunnel'  # replace with your actual path
```

Search with MCP inside Codex: use `$sci-literature` and request keyword searches. Or Crossref metadata fallback:

```powershell
python -X utf8 $skillScript search 'XFEM pre-existing radial crack shield tunnel surcharge' --since 2021-01-01 --limit 15 --out literature/candidates.json
```

After **checking the actual paper and its DOI**, import by replacing the placeholder:

```powershell
python -X utf8 $skillScript import --doi '10.REAL_DOI/REPLACE_ME' --bib references.bib --ledger literature/doi-ledger.json
python -X utf8 $skillScript verify --bib references.bib --ledger literature/doi-ledger.json --out literature/verification.json
```

Prepare `literature/citation-plan.json` from the installed Skill `assets/plan.template.json` or the distribution `examples/plan.template.json`. Use verified citation keys and actual claim evidence. The plan defaults to `approved=false`. Review the evidence and approve individual insertions before marking them true.

```powershell
# Preview changes; no write
python -X utf8 $skillScript insert --root . --bib references.bib --ledger literature/doi-ledger.json --plan literature/citation-plan.json
# Explicitly apply approved changes only, after checking the diff
python -X utf8 $skillScript insert --root . --bib references.bib --ledger literature/doi-ledger.json --plan literature/citation-plan.json --apply
# Audit cited and bibliography keys (offline)
python -X utf8 $skillScript audit --root . --bib references.bib --out literature/citation-audit.json
```

For multiple `.bib` resources, repeat `--bib` for `audit`. `insert` currently validates against **one** `.bib` at a time; choose the file holding the cited entries.

## LaTeX compilation examples

- `natbib` or journal-provided BibTeX templates: compile using journal-prescribed sequence, often `latexmk -pdf main.tex` (automatic bibliography backend handling depends on template/config).
- `biblatex` + `biber`: `latexmk -pdf main.tex` when configured with `backend=biber`; otherwise run `pdflatex main.tex; biber main; pdflatex main.tex; pdflatex main.tex`.
- Never force `biblatex` into an existing Elsevier journal class. Honor the manuscript's own class and bibliography rules.

## How safe insertion works

- The insertion plan needs a real BibTeX key, Crossref DOI status `metadata_verified` in the ledger, and a separate actual evidence record per citation (`abstract` or `full_text`, `direct` relation, locator, finding).
- The source anchor must be a unique exact string in the active text of one `.tex` file; comments and `verbatim`/`lstlisting`/`minted`/`comment` environments are masked. Complicated custom macros require manual review.
- Default `insert` is read-only dry-run. Approved `--apply` creates `.tex.bak.YYYYMMDD-HHMMSS` backups.
- Existing `.bib` text is left untouched unless adding a DOI. The scanner is a practical subset of BibTeX and may need manual checks with `@string`, concatenation, and custom citation macros.
- All references still need scholarly evaluation. Crossref is not an SCIE indexing database and is not a conclusive retraction registry.

## Self-test

```powershell
python -X utf8 -m unittest discover -s .\tests -v
```

Tests do not require network. Live MCP startup, source API availability, indexing status and TeX compilation against a particular publisher template must be verified on your own environment.

## Troubleshooting

- `uvx not found`: install uv and reopen PowerShell/IDE to refresh PATH.
- `paper-search MCP unavailable`: run `codex mcp list`; check `~/.codex/config.toml` and restart Codex. Use a full `uvx.exe` path if necessary.
- HTTP 429/503: follow provider rate limits; set optional API keys where officially available; do not retry aggressively.
- `metadata_mismatch`: inspect the Crossref record and bibliography carefully, especially titles, versions and corrections. Stop automatic citation insertion for that key.
- `anchor must ... exactly once`: use a unique exact full sentence from active TeX; do not force a global replace.
- `Missing citation key`: import the verified DOI into the specified bibliography or correct the citation key.
- `Unicode` issues: consider a LuaLaTeX/XeLaTeX + Biber toolchain if the journal permits; for BibTeX/Natbib, transliterate or escape problematic names manually.

## Project notes and boundaries

- No fabricated citations, unsupported extrapolation, SCI indexing promises or automatic publication eligibility claims.
- `verify` checks DOI, title and publication year; it does not automatically verify that two studies have equivalent experimental conditions.
- If using Zotero Better BibTeX automatic exports, add a separate `codex-added.bib` or import into Zotero first instead of editing the generated export directly.

## References

- Codex skills: https://developers.openai.com/codex/skills
- Codex configuration: https://developers.openai.com/codex/config-basic
- Paper Search MCP: https://github.com/openags/paper-search-mcp
- Crossref REST API: https://api.crossref.org/
- Zotero Better BibTeX automatic export: https://retorque.re/zotero-better-bibtex/preferences/automatic-export/index.html