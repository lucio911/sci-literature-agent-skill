#!/usr/bin/env python3
"""Portable installer for the canonical sci-literature Agent Skill."""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime

SOURCE = Path(__file__).resolve().parents[1] / "skills" / "sci-literature"
HOSTS = {
    "codex": (".agents", ".agents"),
    "claude": (".claude", ".claude"),
    "workbuddy": (".codebuddy", ".codebuddy"),
    "gemini": (".gemini", ".gemini"),
    "opencode": (".config/opencode", ".opencode"),
}

def targets(agent, scope, project_root, home):
    names = list(HOSTS) if agent == "all" else [agent]
    root = home if scope == "user" else project_root
    return [root / HOSTS[n][0 if scope == "user" else 1] / "skills" / "sci-literature" for n in names]

def install(source, target, force=False, dry_run=False):
    if not (source / "SKILL.md").is_file():
        raise FileNotFoundError("Canonical Skill is missing")
    if target.exists() and not force:
        raise FileExistsError("Installed Skill exists; use --force: " + str(target))
    if dry_run:
        return "Would install: " + str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target.rename(target.with_name("sci-literature.backup." + stamp))
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return "Installed: " + str(target)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agent", choices=[*HOSTS, "all"], default="all")
    p.add_argument("--scope", choices=["user", "project"], default="user")
    p.add_argument("--project-root", default=".")
    p.add_argument("--target-dir", help="Other host location ending in sci-literature")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.target_dir:
        dest = Path(a.target_dir).expanduser().resolve()
        if dest.name != "sci-literature":
            p.error("--target-dir must end in sci-literature")
        ds = [dest]
    else:
        ds = targets(a.agent, a.scope, Path(a.project_root).resolve(), Path.home())
    if not a.force and any(d.exists() for d in ds):
        print("Refusing to overwrite existing Skill; supply --force.", file=sys.stderr)
        return 2
    for d in ds:
        print(install(SOURCE, d, force=a.force, dry_run=a.dry_run))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
