---
name: commit
description: Create a conventional commit. Analyzes the current working tree diff and creates a commit with a conventional commit message. Use when the user asks to commit changes.
disable-model-invocation: true
context: fork
agent: commit-writer
allowed-tools: ["Bash(git add:*)", "Bash(git commit:*)", "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git branch:*)", "Bash(git rev-parse:*)"]
---

Analyze the current working tree and create exactly one git commit with a conventional-commit-formatted message. Follow every rule in your system prompt. Return only the final summary line.

Arguments (if any): $ARGUMENTS
