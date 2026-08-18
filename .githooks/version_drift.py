#!/usr/bin/env python3
"""
Verify that every plugin's marketplace version matches its own plugin.json.

  - local entries  (source: "./plugins/<name>")      -> read from disk
  - github entries (source: {source: github, repo})  -> read from the remote

Run directly to check the working tree:  python3 .githooks/version_drift.py
The pre-commit hook calls it with the repo root as its argument.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request

RAW = "https://raw.githubusercontent.com/{repo}/HEAD/.claude-plugin/plugin.json"
API = "https://api.github.com/repos/{repo}/contents/.claude-plugin/plugin.json"
TIMEOUT = 5


def fetch_raw(repo):
    """Fast path. Cheap and unmetered, but CDN-cached: raw sends
    `cache-control: max-age=300`, so for up to five minutes after a push it
    still serves the PREVIOUS commit's file."""
    with urllib.request.urlopen(RAW.format(repo=repo), timeout=TIMEOUT) as resp:
        return json.load(resp).get("version")


def fetch_api(repo):
    """Authoritative path. Metered (60/h anonymous) but not CDN-cached, so it
    reflects a push immediately. Only used to adjudicate a mismatch."""
    req = urllib.request.Request(
        API.format(repo=repo),
        headers={"Accept": "application/vnd.github+json", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        payload = json.load(resp)
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(content).get("version")


NET_ERRORS = (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, KeyError, ValueError)


class Unconfirmed(Exception):
    """raw reported a mismatch that the API could not adjudicate."""


def remote_version(repo, expected, raw=fetch_raw, api=fetch_api):
    """Resolve the remote version, adjudicating a mismatch against the API.

    A raw result that already matches is trusted as-is: staleness can only make
    raw look OLDER than reality, so it can produce a false mismatch but never a
    false match. That keeps the happy path free of API calls.

    Raises on an unreachable remote, or Unconfirmed when raw says "drift" but
    the API cannot be reached to confirm it.
    """
    version = raw(repo)
    if version == expected:
        return version, None
    try:
        return api(repo), "confirmed against the API (raw is CDN-cached for 5m)"
    except NET_ERRORS as e:
        raise Unconfirmed(version, e) from e


def check(repo_root, raw=fetch_raw, api=fetch_api):
    """Return a list of human-readable error strings (empty when consistent)."""
    marketplace_path = os.path.join(repo_root, ".claude-plugin", "marketplace.json")
    with open(marketplace_path, "r", encoding="utf-8") as f:
        marketplace = json.load(f)

    errors = []

    for entry in marketplace.get("plugins", []):
        name = entry.get("name")
        marketplace_version = entry.get("version")

        if not name:
            errors.append("marketplace.json has a plugin entry with no 'name' field")
            continue
        if not marketplace_version:
            errors.append(f"marketplace.json entry '{name}' has no 'version' field")
            continue

        source = entry.get("source")
        if isinstance(source, dict) and source.get("source") == "github":
            repo = source.get("repo")
            if not repo:
                errors.append(f"plugin '{name}': github source has no 'repo' field")
                continue
            try:
                plugin_version, note = remote_version(repo, marketplace_version, raw, api)
            except Unconfirmed as e:
                seen, cause = e.args
                print(
                    f"pre-commit: warning: '{name}' looks like drift "
                    f"(marketplace {marketplace_version}, remote {seen}) but the API "
                    f"could not confirm it ({cause}). raw is CDN-cached for 5 minutes, "
                    f"so this is expected right after a push — NOT blocking. If you did "
                    f"not just push, treat it as real drift.",
                    file=sys.stderr,
                )
                continue
            except NET_ERRORS as e:
                print(
                    f"pre-commit: warning: could not verify remote plugin '{name}' "
                    f"({repo}): {e} — skipping cross-repo check.",
                    file=sys.stderr,
                )
                continue
            source_label = f"{repo} plugin.json (remote)"
            if note:
                source_label += f", {note}"
        else:
            plugin_json_path = os.path.join(
                repo_root, "plugins", name, ".claude-plugin", "plugin.json"
            )
            if not os.path.isfile(plugin_json_path):
                errors.append(
                    f"plugin '{name}': plugin.json missing at plugins/{name}/.claude-plugin/plugin.json"
                )
                continue
            try:
                with open(plugin_json_path, "r", encoding="utf-8") as f:
                    plugin_json = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"plugin '{name}': plugin.json is not valid JSON: {e}")
                continue
            plugin_version = plugin_json.get("version")
            source_label = f"plugins/{name}/.claude-plugin/plugin.json"

        if not plugin_version:
            errors.append(
                f"plugin '{name}': plugin.json has no 'version' field "
                f"(marketplace declares {marketplace_version})"
            )
            continue

        if plugin_version != marketplace_version:
            errors.append(
                f"plugin '{name}': version drift\n"
                f"  marketplace.json:  {marketplace_version}\n"
                f"  {source_label}:  {plugin_version}"
            )

    return errors


def main(argv):
    repo_root = argv[1] if len(argv) > 1 else os.getcwd()
    errors = check(repo_root)
    if not errors:
        return 0
    print("pre-commit: plugin manifest version drift detected", file=sys.stderr)
    print("", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Sync marketplace.json and plugin.json before committing. "
        "See CLAUDE.md 'Version bumping discipline'.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
