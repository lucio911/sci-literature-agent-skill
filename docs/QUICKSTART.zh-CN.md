# SCI Literature for Codex — Windows 快速入门

> 本项目是 Codex Skill + Python 引用工具。它不是 MCP 服务器；文献检索能力由可选的 [Paper Search MCP](https://github.com/openags/paper-search-mcp) 提供。

## 功能

- 文献搜索：Paper Search MCP 优先；Crossref 元数据搜索回退。
- DOI 身份核验：比对题名、年份和 DOI，记录可能冲突。
- BibTeX：按 DOI 幂等导入、去重、维护稳定 citation key。
- LaTeX：先生成引用计划与证据表，经确认后预览修改，再插入 `\cite{key}` 等命令。
- 审计：检查缺失 citation key、重复 DOI、重复 BibTeX key、未使用条目。

**边界**：DOI 查到不代表文献确实支持观点；阅读摘要或全文才能判断。也不能把 Crossref 检索当作 Web of Science/SCIE 收录证明。

## 依赖

Windows 10/11、Codex、Python 3.10+。文献 MCP 需要 `uvx`（来自 uv），编译需要 MiKTeX 或 TeX Live。

## 安装

在本仓库目录打开 PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Scope User -InstallMcp
codex mcp list
```

或者仅安装到指定项目：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Scope Project -ProjectRoot 'D:\papers\tunnel'
```

重新启动 Codex，在项目中用 `$sci-literature` 唤起 Skill。

## 典型工作流程

```powershell
$script = Join-Path $HOME '.agents\skills\sci-literature\scripts\sci_refs.py'
python -X utf8 $script search 'XFEM cracked tunnel lining surface surcharge' --since 2021-01-01 --limit 15 --out literature/candidates.json
# 替换成检索并核实的真实 DOI
python -X utf8 $script import --doi '10.REPLACE/REAL-DOI' --bib references.bib --ledger literature/doi-ledger.json
python -X utf8 $script verify --bib references.bib --ledger literature/doi-ledger.json --out literature/verification.json
# 依据 examples/plan.template.json 建立经用户确认的引用计划
python -X utf8 $script insert --root . --bib references.bib --ledger literature/doi-ledger.json --plan literature/citation-plan.json
# 检查 diff 后再执行真实插入
python -X utf8 $script insert --root . --bib references.bib --ledger literature/doi-ledger.json --plan literature/citation-plan.json --apply
python -X utf8 $script audit --root . --bib references.bib --out literature/citation-audit.json
```

## 给 Codex 的任务示例

> 使用 `$sci-literature` 检查当前 LaTeX 论文引言中需要文献支持的论点，搜索近五年相关同行评审论文及必要的经典研究。先核对 DOI 和研究工况，再从真实摘要/全文建立论点—证据表。只输出引用计划与 dry-run diff，不要直接修改 .tex 或 .bib 中既有内容。等待我确认后才能执行引用插入，并运行审计和期刊模板编译。

详细安装与边界见 [README.md](../README.md) 和 [SKILL.md](../skill/SKILL.md)。
