#!/usr/bin/env python3
"""Estimate what a Claude Code session loads before the first prompt.

Usage: loaded_cost.py [PROJECT_DIR] [--json]

Counts characters of always-loaded instruction files, the auto-memory index,
and the skill / agent descriptions of every enabled plugin and user / project
skill. Read-only. An estimate: a project's own counter (e.g. an instruction
lint) wins where it exists. Tokens ~= chars / 3.5.
"""
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE = HOME / ".claude"


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def split_frontmatter(text):
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[4:end], text[end + 4:].lstrip("\n")
    return "", text


def fm_value(fm, key):
    """Value of a top-level YAML key, folded/quoted forms flattened."""
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", fm, re.M)
    if not m:
        return ""
    val = m.group(1).strip()
    if val in (">", "|", ">-", "|-", ""):
        lines = []
        for line in fm[m.end() + 1:].splitlines():
            if line.startswith((" ", "\t")) or not line.strip():
                lines.append(line.strip())
            else:
                break
        val = " ".join(x for x in lines if x)
    return val.strip("'\"")


def body_chars(path):
    text = read(path)
    if text is None:
        return 0
    _, body = split_frontmatter(text)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    return len(body)


def is_path_scoped(path):
    fm, _ = split_frontmatter(read(path) or "")
    return bool(re.search(r"^paths:", fm, re.M))


def skill_listing_chars(skill_md):
    fm, _ = split_frontmatter(read(skill_md) or "")
    if fm_value(fm, "disable-model-invocation").lower() == "true":
        return 0
    desc = fm_value(fm, "description") + fm_value(fm, "when_to_use")
    return min(len(desc), 1536) + len(fm_value(fm, "name") or Path(skill_md).parent.name)


def agent_listing_chars(agent_md):
    fm, _ = split_frontmatter(read(agent_md) or "")
    return len(fm_value(fm, "description")) + len(fm_value(fm, "name"))


def load_json(p):
    t = read(p)
    if not t:
        return {}
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return {}


def enabled_plugins(project):
    merged = {}
    for f in (CLAUDE / "settings.json", project / ".claude/settings.json",
              project / ".claude/settings.local.json"):
        merged.update(load_json(f).get("enabledPlugins", {}) or {})
    return [k for k, v in merged.items() if v]


def install_path(plugin_key, project):
    entries = load_json(CLAUDE / "plugins/installed_plugins.json").get("plugins", {}).get(plugin_key, [])
    best = None
    for e in entries:
        if e.get("projectPath") and Path(e["projectPath"]).resolve() == project.resolve():
            return Path(e["installPath"])
        if e.get("scope") == "user" or best is None:
            best = Path(e["installPath"])
    return best


def plugin_cost(root):
    skills = sum(skill_listing_chars(p) for p in root.glob("skills/*/SKILL.md"))
    skills += sum(skill_listing_chars(p) for p in root.glob("commands/*.md"))
    agents = sum(agent_listing_chars(p) for p in root.glob("agents/*.md"))
    return skills, agents


def memory_dir(project):
    return CLAUDE / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(project)) / "memory"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    project = Path(args[0] if args else ".").resolve()
    rows = []

    def add(group, item, chars, note=""):
        rows.append({"group": group, "item": item, "chars": chars, "note": note})

    # Instruction files: user scope, then every directory from / down to the project.
    add("instructions", "~/.claude/CLAUDE.md", body_chars(CLAUDE / "CLAUDE.md"))
    for r in sorted((CLAUDE / "rules").glob("**/*.md")):
        if not is_path_scoped(r):
            add("instructions", f"~/.claude/rules/{r.relative_to(CLAUDE / 'rules')}", body_chars(r))
    chain = list(reversed([project, *project.parents]))
    for d in chain:
        for name in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
            p = d / name
            if p.is_file() and p != CLAUDE / "CLAUDE.md":
                add("instructions", str(p), body_chars(p))
    if not any((d / "CLAUDE.md").is_file() or (d / "CLAUDE.local.md").is_file() for d in chain):
        if (project / "AGENTS.md").is_file():
            add("instructions", str(project / "AGENTS.md"), body_chars(project / "AGENTS.md"))
    scoped = 0
    for r in sorted((project / ".claude/rules").glob("**/*.md")):
        if is_path_scoped(r):
            scoped += 1
        else:
            add("instructions", str(r.relative_to(project)), body_chars(r))

    idx = memory_dir(project) / "MEMORY.md"
    if idx.is_file():
        lines = (read(idx) or "").splitlines()[:200]
        add("memory", str(idx).replace(str(HOME), "~"), min(len("\n".join(lines)), 25_000), "first 200 lines / 25 KB")

    for key in sorted(enabled_plugins(project)):
        root = install_path(key, project)
        if root is None or not root.is_dir():
            add("plugins", key, 0, "enabled but not installed")
            continue
        s, a = plugin_cost(root)
        add("plugins", key, s + a, f"skills {s}, agents {a}")

    for base, label in ((CLAUDE / "skills", "~/.claude/skills"), (project / ".claude/skills", ".claude/skills")):
        for p in sorted(base.glob("*/SKILL.md")):
            add("skills", f"{label}/{p.parent.name}", skill_listing_chars(p))
    for base, label in ((CLAUDE / "agents", "~/.claude/agents"), (project / ".claude/agents", ".claude/agents")):
        for p in sorted(base.glob("*.md")):
            add("agents", f"{label}/{p.name}", agent_listing_chars(p))

    if "--json" in sys.argv:
        print(json.dumps({"project": str(project), "rows": rows, "path_scoped_rules": scoped}, indent=1))
        return
    total = sum(r["chars"] for r in rows)
    print(f"project: {project}")
    for g in ("instructions", "memory", "plugins", "skills", "agents"):
        sub = [r for r in rows if r["group"] == g]
        if not sub:
            continue
        gt = sum(r["chars"] for r in sub)
        print(f"\n{g}: {gt:,} chars (~{gt / 3.5:,.0f} tok)")
        for r in sorted(sub, key=lambda r: -r["chars"]):
            note = f"  [{r['note']}]" if r["note"] else ""
            print(f"  {r['chars']:>8,}  {r['item']}{note}")
    print(f"\npath-scoped rules (load on demand, not counted): {scoped}")
    print(f"TOTAL ~{total:,} chars (~{total / 3.5:,.0f} tokens) before the first prompt, excluding the harness's own prompt")


if __name__ == "__main__":
    main()
