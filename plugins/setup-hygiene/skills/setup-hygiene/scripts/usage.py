#!/usr/bin/env python3
"""Count what sessions actually USED, from Claude Code transcripts.

Usage: usage.py [PROJECT_DIR | --all] [--since YYYY-MM-DD] [--json]

Counts real invocations, never tool listings: Skill tool calls (by skill),
Agent/Task calls (by subagent_type), MCP tool calls (by server), and slash
commands the user typed. Subagent transcripts are included. Read-only.

Each plugin-qualified row (`plugin:name`, or an MCP server `plugin_<plugin>_*`)
is marked with the plugin's enabled state today, from the local, project and
user settings in that precedence; user settings are always read, and --all
reads only them (it has no single project). A count for a plugin that is now
disabled is history, not a live path.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECTS = Path.home() / ".claude/projects"
USER_SETTINGS = Path.home() / ".claude/settings.json"
CMD = re.compile(r"<command-name>/?([^<\s]+)</command-name>")


def project_key(path):
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(path).resolve()))


def enabled_plugins(project):
    """Plugin name -> True/False, local > project > user; any marketplace enabled wins."""
    files = [USER_SETTINGS]
    if project:
        files += [Path(project) / ".claude/settings.json", Path(project) / ".claude/settings.local.json"]
    state = {}
    for f in files:  # later files override earlier ones
        try:
            plugins = json.loads(f.read_text()).get("enabledPlugins") or {}
        except (OSError, ValueError, AttributeError):
            continue
        scope = {}
        for key, on in plugins.items():
            name = key.split("@", 1)[0]
            scope[name] = scope.get(name, False) or bool(on)
        state.update(scope)
    return state


def plugin_of(kind, key, known):
    """The plugin a row belongs to, or None for built-in / user / project items."""
    if kind == "mcp":
        if not key.startswith("plugin_"):
            return None
        rest = key[len("plugin_"):]
        hits = [p for p in known if rest == p or rest.startswith(p + "_")]
        return max(hits, key=len) if hits else rest.split("_", 1)[0]
    if kind in ("skill", "agent", "slash") and ":" in key:
        return key.split(":", 1)[0]
    return None


def mark(kind, key, state):
    plugin = plugin_of(kind, key, state)
    if plugin is None:
        return None
    return {True: "enabled", False: "disabled"}.get(state.get(plugin), "not in settings")


def arg(flag):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    return None


def main():
    since = arg("--since")
    since_ts = datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp() if since else 0
    positional = [a for a in sys.argv[1:] if not a.startswith("--") and a != since]
    project = None if "--all" in sys.argv else (positional[0] if positional else ".")
    if project is None:
        dirs = [d for d in PROJECTS.iterdir() if d.is_dir()]
    else:
        d = PROJECTS / project_key(project)
        if not d.is_dir():
            sys.exit(f"no transcripts at {d}")
        dirs = [d]

    counts = defaultdict(Counter)
    sessions = defaultdict(set)  # "kind:name" -> session ids
    n_sessions = 0
    for d in dirs:
        for f in d.glob("**/*.jsonl"):
            if f.stat().st_mtime < since_ts:
                continue
            sid = f.stem if f.parent == d else f.parent.parent.name
            if f.parent == d:
                n_sessions += 1
            try:
                lines = f.open(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in lines:
                if '"tool_use"' not in line and "command-name" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if rec.get("type") == "user":
                    text = content if isinstance(content, str) else " ".join(
                        b.get("text", "") for b in content or [] if isinstance(b, dict))
                    for name in CMD.findall(text):
                        counts["slash"][name] += 1
                        sessions["slash:" + name].add(sid)
                    continue
                if not isinstance(content, list):
                    continue
                for b in content:
                    if not isinstance(b, dict) or b.get("type") != "tool_use":
                        continue
                    name, inp = b.get("name", ""), b.get("input") or {}
                    if name == "Skill":
                        kind, key = "skill", inp.get("skill", "?")
                    elif name in ("Agent", "Task"):
                        kind, key = "agent", inp.get("subagent_type") or "general-purpose"
                    elif name.startswith("mcp__"):
                        kind, key = "mcp", name.split("__")[1]
                    else:
                        kind, key = "tool", name
                    counts[kind][key] += 1
                    sessions[f"{kind}:{key}"].add(sid)

    state = enabled_plugins(project)
    if "--json" in sys.argv:
        out = {}
        for k, v in counts.items():
            out[k] = {}
            for n, c in v.items():
                row = {"calls": c, "sessions": len(sessions[f"{k}:{n}"])}
                m = mark(k, n, state)
                if m:
                    row["plugin_state"] = m
                out[k][n] = row
        print(json.dumps(out | {"_sessions": n_sessions}, indent=1))
        return
    print(f"sessions scanned: {n_sessions}" + (f" (since {since})" if since else ""))
    print("plugin state: " + ("user settings only" if project is None else "local > project > user settings"))
    for kind in ("slash", "skill", "agent", "mcp", "tool"):
        if not counts[kind]:
            continue
        print(f"\n{kind}:  calls  sessions")
        for name, c in counts[kind].most_common(40 if kind != "tool" else 15):
            m = mark(kind, name, state)
            print(f"  {c:>6}  {len(sessions[f'{kind}:{name}']):>6}  {name}" + (f"  [{m}]" if m else ""))


if __name__ == "__main__":
    main()
