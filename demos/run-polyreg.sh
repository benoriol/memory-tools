#!/usr/bin/env bash
# End-to-end memory-graph demo runner.
#
#   1. Make a fresh demo workspace at /tmp/memory-graph-demo-polyreg-<ts>
#   2. Copy the polyreg/ task into it
#   3. Run `memory-graph setup` (no token; relies on `claude /login`)
#   4. Run `claude -p` against CLAUDE.md so the agent works the task
#   5. Snapshot the resulting memory graph
#   6. Print a summary; tell the user how to open the viz
#
# Usage:   bash demos/run-polyreg.sh [--viz-port 8765]
#
# Requires:
#   - `memory-graph` and `claude` on PATH
#   - `claude /login` previously done (~/.claude/.credentials.json present)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/demos/polyreg"
VIZ_PORT=8765

while [[ $# -gt 0 ]]; do
    case "$1" in
        --viz-port) VIZ_PORT="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

if ! command -v memory-graph >/dev/null; then
    echo "memory-graph not on PATH. Install with: pipx install -e $REPO_ROOT" >&2
    exit 1
fi
if ! command -v claude >/dev/null; then
    echo "claude (Claude Code CLI) not on PATH." >&2
    exit 1
fi
if [[ ! -f "$HOME/.claude/.credentials.json" ]]; then
    echo "no ~/.claude/.credentials.json — run \`claude /login\` first." >&2
    exit 1
fi

TS=$(date +%Y%m%d-%H%M%S)
WORKDIR="/tmp/memory-graph-demo-polyreg-$TS"
mkdir -p "$WORKDIR"

echo "==> demo workdir: $WORKDIR"
cp "$TEMPLATE_DIR/CLAUDE.md" "$WORKDIR/"
cp "$TEMPLATE_DIR/data.py"   "$WORKDIR/"

echo
echo "==> setting up memory-graph in workdir (no baked token; uses /login)"
( cd "$WORKDIR" && memory-graph setup --force )

echo
echo "==> launching agent via 'claude -p' (this is the part that takes time)"
echo "    target: ~10 minutes of work, ~6-12 memory writes expected"

# Hand the agent a single concise kickoff prompt. CLAUDE.md drives the rest.
KICKOFF='Read CLAUDE.md and complete the polynomial regression sweep.
Use the memory_* tools liberally as instructed. When you finish, print
the best degree per noise level plus your generalization, and the ids
of memories you wrote.'

# bypassPermissions is appropriate here: this is an isolated tmp workdir
# and the only "dangerous" tools the agent needs are the memory_* MCP
# tools, which write to .memory-graph/ inside this same workdir.
( cd "$WORKDIR" && claude -p "$KICKOFF" --permission-mode bypassPermissions ) \
    2>&1 | tee "$WORKDIR/agent-output.log" || {
    echo "agent run finished with non-zero exit; continuing to snapshot anyway" >&2
}

echo
echo "==> agent done — snapshotting memory graph"
( cd "$WORKDIR" && memory-graph status )

NOTES=$(ls "$WORKDIR/.memory-graph/notes/"*.md 2>/dev/null | wc -l)
echo
echo "==> notes on disk: $NOTES"
echo "    workdir:        $WORKDIR"
echo "    open the viz:"
echo "        cd $WORKDIR && memory-graph viz --port $VIZ_PORT"
echo
echo "    (the viz is not auto-started by this script; run it yourself"
echo "     when ready and refresh the browser)"
