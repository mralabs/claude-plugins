---
name: commit
description: Create a conventional commit. Analyzes the current working tree diff and creates a commit with a conventional commit message. Supports --pr (push + open PR) and --merge/--m/--prm (PR + squash merge).
disable-model-invocation: true
context: fork
agent: commit:commit-writer
allowed-tools: ["Bash(git add:*)", "Bash(git commit:*)", "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git branch:*)", "Bash(git rev-parse:*)", "Bash(git remote get-url:*)", "Bash(git checkout -b:*)", "Bash(git push -u origin:*)", "Bash(git pull --ff-only:*)", "Bash(gh pr create:*)", "Bash(gh pr merge:*)", "Bash(gh pr view:*)"]
---

Analyze the current working tree and create exactly one git commit with a conventional-commit-formatted message. Follow every rule in your system prompt, including the PR/merge flag handling when the arguments below carry --pr, --merge, --m, or --prm. Return only the final summary line.

Arguments (if any): $ARGUMENTS
