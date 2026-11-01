#!/usr/bin/env python3
"""Opt-in Paper Search MCP setup. Keeps existing WorkBuddy settings intact."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def merge_workbuddy_mcp(path, apply=False):
    obj = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    if not isinstance(obj, dict) or not isinstance(obj.get("mcpServers", {}), dict):
        raise ValueError("Invalid MCP config; refusing overwrite: " + str(path))
    servers = obj.setdefault("mcpServers", {})
    if "paper-search" in servers:
        return "Existing WorkBuddy paper-search retained"
    if not apply:
        return "Would add paper-search to " + str(path)
    if path.exists():
        backup = path.with_name(path.name + ".backup." + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        shutil.copy2(path, backup)
    servers["paper-search"] = {"command": "uvx", "args": ["paper-search-mcp"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return "Configured WorkBuddy: " + str(path)

def configure_cli(agent, scope, apply=False):
    exe = "codex" if agent == "codex" else "claude"
    if shutil.which(exe) is None:
        return "WARNING: " + exe + " CLI not installed; configure MCP manually"
    listed = subprocess.run([exe, "mcp", "list"], capture_output=True, text=True, check=False)
    if listed.returncode == 0 and "paper-search" in listed.stdout:
        return "Existing paper-search retained for " + agent
    if agent == "codex":
        cmd = [exe, "mcp", "add", "paper-search", "--", "uvx", "paper-search-mcp"]
    else:
        cmd = [exe, "mcp", "add", "--scope", scope, "--transport", "stdio",
               "paper-search", "--", "uvx", "paper-search-mcp"]
    if not apply:
        return "Would run: " + " ".join(cmd)
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if done.returncode:
        raise RuntimeError("MCP setup failed for " + agent + ": " + done.stderr.strip())
    return "Configured " + agent

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agent", choices=["codex","claude","workbuddy","gemini","opencode","all"], default="all")
    p.add_argument("--scope", choices=["user", "project"], default="user")
    p.add_argument("--project-root", default=".")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    if not shutil.which("uvx"):
        if a.apply:
            print("ERROR: uvx not installed; install uv first", file=sys.stderr)
            return 2
        print("WARNING: uvx not installed", file=sys.stderr)
    names = ["codex","claude","workbuddy","gemini","opencode"] if a.agent == "all" else [a.agent]
    for n in names:
        if n == "workbuddy":
            root = Path.home() if a.scope == "user" else Path(a.project_root).resolve()
            print(merge_workbuddy_mcp(root / ".workbuddy" / "mcp.json", apply=a.apply))
        elif n in ("codex","claude"):
            print(configure_cli(n, a.scope, apply=a.apply))
        else:
            print("NOTE: " + n + " requires manual MCP configuration; Skill works without MCP")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as e:
        print("ERROR: " + str(e), file=sys.stderr)
        raise SystemExit(2)
