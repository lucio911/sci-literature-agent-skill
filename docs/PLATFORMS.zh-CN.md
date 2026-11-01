# 跨智能体安装：Codex / Claude Code / WorkBuddy / Gemini / OpenCode

本仓库遵循 Agent Skills 标准。只维护一套科研工作流和 Python 脚本：skills/sci-literature。Paper Search MCP 是单独可选的第三方检索服务，不属于本仓库自建 MCP。

## Windows 安装

克隆仓库并在其根目录的 PowerShell 执行：

    git clone https://github.com/lucio911/sci-literature-codex.git
    cd sci-literature-codex
    .\install.ps1 -Agent All -Scope User

只给一个项目安装：

    .\install.ps1 -Agent Claude -Scope Project -ProjectRoot 'D:\papers\manuscript'

需要升级已安装的 Skill 时使用 -Force。升级之前会自动备份已有副本。默认不安装 MCP；如需同时安装检索 MCP：

    .\install.ps1 -Agent All -Scope User -Force -InstallMcp

跨系统 Python 安装：

    python scripts/install_skill.py --agent all --scope user
    python scripts/install_skill.py --agent all --scope user --dry-run
    python scripts/install_skill.py --target-dir /custom/agent/skills/sci-literature

## Skill 目录

- Codex: ~/.agents/skills/sci-literature 或 <project>/.agents/skills/sci-literature
- Claude Code: ~/.claude/skills/sci-literature 或 <project>/.claude/skills/sci-literature
- WorkBuddy/CodeBuddy: ~/.codebuddy/skills/sci-literature 或 <project>/.codebuddy/skills/sci-literature
- Gemini CLI: ~/.gemini/skills/sci-literature 或 <project>/.gemini/skills/sci-literature
- OpenCode: ~/.config/opencode/skills/sci-literature 或 <project>/.opencode/skills/sci-literature

WorkBuddy 桌面版也可通过「上传技能包」导入单独的 sci-literature Skill ZIP；需要本地 Python 执行权限才能自动修改 LaTeX 文件。

## 检索 MCP

需先安装 uv（uvx）；安装只在用户显式要求时进行。推荐先检查上游代码：https://github.com/openags/paper-search-mcp 。

Codex:

    codex mcp add paper-search -- uvx paper-search-mcp

Claude Code:

    claude mcp add --scope user --transport stdio paper-search -- uvx paper-search-mcp

WorkBuddy（用户级 ~/.workbuddy/mcp.json，项目级 <project>/.workbuddy/mcp.json）在现有 mcpServers 下新增，不能覆盖原有配置：

    {"mcpServers":{"paper-search":{"command":"uvx","args":["paper-search-mcp"]}}}

Windows 的 -InstallMcp 会为 WorkBuddy 合并配置并预先备份旧文件；Gemini 和 OpenCode 的 MCP 配置需要在对应平台手动完成。MCP 不可用时，Python 仍可执行 Crossref metadata 查询以及离线引用审计。

## 启用

- Codex 对话：$sci-literature 检索可核验文献并提出引用修改计划。
- Claude Code 对话：/sci-literature 核对 DOI 并审查引文证据。
- WorkBuddy 对话：请使用 sci-literature 技能为当前 .tex 论文整理可核验参考文献，先提供修改预览。
- Gemini/OpenCode：使用宿主的技能选择器或自然语言指明 sci-literature。

## 边界

- DOI metadata 验证不代表全文证据匹配，也不意味着 SCI/SCIE 收录。
- 必须先验证论点证据，并由用户确认变更计划，方可执行 --apply。
- 不会自动绕过付费墙，不会编造引文和源数据，不会修改用户既有 MCP 凭证。

## 官方参考

https://agentskills.io/specification
https://code.claude.com/docs/en/skills
https://code.claude.com/docs/en/mcp
https://learn.chatgpt.com/docs/build-skills
https://www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project
https://www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide
https://geminicli.com/docs/cli/skills/
https://opencode.ai/docs/skills
