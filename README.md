# SCI Literature — Universal Agent Skill for LaTeX & BibTeX

**One Agent Skill for Codex, Claude Code, WorkBuddy/CodeBuddy, Gemini CLI, OpenCode, and compatible AI agents.**

A conservative academic reference workflow that searches papers, verifies DOI metadata, maps evidence to claims, safely updates `.bib` and `.tex`, and audits citation integrity. Uses the open [Agent Skills specification](https://agentskills.io/specification). An optional [Paper Search MCP](https://github.com/openags/paper-search-mcp) increases discovery coverage; the skill does **not** implement its own MCP server.

[中文跨平台安装指南](docs/PLATFORMS.zh-CN.md) · [完整使用指南](docs/QUICKSTART.zh-CN.md) · [Skill](skills/sci-literature/SKILL.md) · [质量门槛](skills/sci-literature/references/QUALITY-GATES.md)

## Supported hosts

| Host | Per-user skill directory | Project-local skill directory |
|---|---|---|
| OpenAI Codex | `~/.agents/skills/sci-literature/` | `.agents/skills/sci-literature/` |
| Anthropic Claude Code | `~/.claude/skills/sci-literature/` | `.claude/skills/sci-literature/` |
| Tencent WorkBuddy / CodeBuddy | `~/.codebuddy/skills/sci-literature/` | `.codebuddy/skills/sci-literature/` |
| Gemini CLI | `~/.gemini/skills/sci-literature/` | `.gemini/skills/sci-literature/` |
| OpenCode | `~/.config/opencode/skills/sci-literature/` | `.opencode/skills/sci-literature/` |
| Other Agent Skills hosts | Import `skills/sci-literature/` | Host-specific |

WorkBuddy editions with a skill-upload interface can import the standalone Skill ZIP, subject to their local execution permissions. Platform support varies by version.

## Quick installation

Requires Python **3.10+**. For PowerShell on Windows:

```powershell
git clone https://github.com/lucio911/sci-literature-codex.git
cd sci-literature-codex
.\install.ps1 -Agent All -Scope User
```

To add Paper Search MCP where supported (optional; requires `uvx`):

```powershell
.\install.ps1 -Agent All -Scope User -InstallMcp -Force
```

For Linux/macOS/Windows via Python:

```bash
python scripts/install_skill.py --agent all --scope user
python scripts/install_skill.py --agent claude --scope project --project-root /path/to/manuscript
```

The installer only copies the canonical Skill to host directories. Gemini CLI and OpenCode additionally discover certain shared `.agents/skills` paths, so choose one preferred copy if duplicate names are displayed. It never installs arbitrary dependencies or changes MCP configuration unless you explicitly pass `-InstallMcp` to the PowerShell installer or run `scripts/configure_mcp.py --apply`. For a different Agent Skills host, pass `--target-dir /path/to/skills/sci-literature` to the Python installer. If a skill already exists, supply `-Force` / `--force`; an existing copy is **backed up** before replacement.

## Usage examples

**Codex:** `$sci-literature Find verified sources for the introduction; propose a plan and show me the diff before editing.`

**Claude Code:** `/sci-literature Review these literature claims and verify DOI metadata; prepare approved-only LaTeX citations.`

**WorkBuddy:** `使用 sci-literature 技能，检索相关论文并核验 DOI，先提供引用证据和改动预览，未经批准不要修改 .tex。`

**Direct Python, no agent required:**

```bash
python skills/sci-literature/scripts/sci_refs.py search "XFEM tunnel lining surcharge" --since 2021-01-01 --limit 15 --out literature/candidates.json
python skills/sci-literature/scripts/sci_refs.py audit --root . --bib references.bib --out literature/citation-audit.json
```

For DOI import, metadata validation, evidence plans, dry-run and approved-only insertion, see [the Chinese guide](docs/QUICKSTART.zh-CN.md) and [SKILL.md](skills/sci-literature/SKILL.md).

## Architecture

```text
sci-literature-codex/
├── skills/
│   └── sci-literature/
│       ├── SKILL.md                   # Vendor-neutral instructions
│       ├── scripts/sci_refs.py        # Deterministic bibliographic operations
│       ├── references/QUALITY-GATES.md
│       └── assets/plan.template.json
├── scripts/
│   ├── install_skill.py               # Platform-agnostic installer
│   └── configure_mcp.py               # Optional MCP setup helper
├── install.ps1                        # Windows wrapper, backwards-compatible flags
├── docs/
│   ├── PLATFORMS.zh-CN.md
│   └── QUICKSTART.zh-CN.md
├── examples/plan.template.json
└── tests/
```

**One canonical Skill source**, copied into each host's appropriate location. No vendor-specific science logic, no separate copies to maintain.

## What it checks

1. Discovers candidates using Paper Search MCP if available, with Crossref metadata search as fallback.
2. Verifies DOI/title/year and checks duplicate bibliography records.
3. Requires direct evidence and a source locator per proposed citation; metadata alone is insufficient.
4. Generates a proposal and previews a diff before insertion; only the user can approve manuscript edits.
5. Preserves existing TeX and BibTeX formatting outside approved changes, and creates backups.
6. Audits unresolved citation keys, duplicate DOIs, bibliography mismatches, and unused records.

No claims of SCI/SCIE indexing, full-text reading, source validity, or successful compilation are made without actual verification.

## Tests

```bash
python -m unittest discover -s tests -v
python scripts/install_skill.py --agent all --scope user --dry-run
```

Test coverage includes citation safety checks and host-installation behavior. CI runs on Windows and Ubuntu. Real MCP connectivity and publisher-template compilation require integration testing in your own host environment.

## Security and compatibility

- `Python 3.10+` standard library only for local scripts; the external `paper-search-mcp` has its own requirements.
- Never check in API keys, OAuth tokens, local `.env` files, user manuscripts, or downloads.
- WorkBuddy `mcp.json` changes are additive and backed up; existing MCP definitions are not overwritten.
- `-InstallMcp` requests execution of an external upstream MCP package. Review upstream code before opting in.
- The initial v1.0 release was Codex-only; v1.1 reorganizes the Skill under `skills/sci-literature/` for cross-agent distribution. The existing GitHub URL remains unchanged.

## License

MIT. See [LICENSE](LICENSE).