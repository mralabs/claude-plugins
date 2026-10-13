#!/usr/bin/env python3
"""Count what sessions actually USED, from Claude Code transcripts.

Usage: usage.py [PROJECT_DIR | --all] [--since YYYY-MM-DD] [--json]

Counts real invocations, never tool listings: Skill tool calls (by skill),
Agent/Task calls (by subagent_type), MCP tool calls (by server), and slash
commands the user typed. Subagent transcripts are included. Read-only.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECTS = Path.home() / ".claude/projects"
CMD = re.compile(r"<command-name>/?([^<\s]+)</command-name>")


def project_key(path):
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(path).resolve()))


def arg(flag):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    return None


def main():
    since = arg("--since")
    since_ts = datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp() if since else 0
    positional = [a for a in sys.argv[1:] if not a.startswith("--") and a != since]
    if "--all" in sys.argv:
        dirs = [d for d in PROJECTS.iterdir() if d.is_dir()]
    else:
        d = PROJECTS / project_key(positional[0] if positional else ".")
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

    if "--json" in sys.argv:
        print(json.dumps({k: {n: {"calls": c, "sessions": len(sessions[f"{k}:{n}"])}
                              for n, c in v.items()} for k, v in counts.items()}
                         | {"_sessions": n_sessions}, indent=1))
        return
    print(f"sessions scanned: {n_sessions}" + (f" (since {since})" if since else ""))
    for kind in ("slash", "skill", "agent", "mcp", "tool"):
        if not counts[kind]:
            continue
        print(f"\n{kind}:  calls  sessions")
        for name, c in counts[kind].most_common(40 if kind != "tool" else 15):
            print(f"  {c:>6}  {len(sessions[f'{kind}:{name}']):>6}  {name}")


if __name__ == "__main__":
    main()
