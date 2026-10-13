#!/usr/bin/env bash
# SessionStart hook: tell the session how many field notes wait in the
# owner's private inbox, so an evolve pass is offered when one is due.
#
# Self-improving plugins (launch-qa, setup-hygiene) append lessons from real
# runs to $CLAUDE_CONFIG_DIR/field-notes/<skill>.md. Nothing in this repo
# sees that inbox unless something counts it here. Read-only; prints nothing
# when there is nothing open; any failure prints nothing (never blocks a
# session).

dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/field-notes"
[ -d "$dir" ] || exit 0

summary=""
due=""
for f in "$dir"/*.md; do
  [ -f "$f" ] || continue
  skill=$(basename "$f" .md)
  # Count open entries outside code fences (the header's format template
  # sits inside a fence). Two formats: launch-qa ends its "## <date> · …"
  # heading with "· open"; setup-hygiene has a "- status: open" line.
  open=$(awk '
    /^```/ { fence = !fence; next }
    fence { next }
    /^## / && /· open[[:space:]]*$/ { n++ }
    /^- status: open[[:space:]]*$/ { n++ }
    END { print n + 0 }
  ' "$f" 2>/dev/null) || continue
  [ "${open:-0}" -gt 0 ] || continue
  summary="${summary:+$summary, }$skill $open open"
  [ "$open" -ge 5 ] && due="${due:+$due, }$skill"
done

[ -n "$summary" ] || exit 0
echo "Field-notes inbox ($dir): $summary."
if [ -n "$due" ]; then
  echo "Due for an evolve pass: $due. Offer the owner \"evolve <skill>\" (CLAUDE.md § Self-improving skills); do not start it unasked."
fi
exit 0
