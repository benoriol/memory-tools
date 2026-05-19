"""Smart orchestration tools backed by the Agent SDK.

The three exposed tools (`remember`, `retrieve`, `compact`) spawn a
memory-specialist sub-agent that has in-process access to the same
memory primitives the MCP server exposes. The main agent calling these
tools only sees the final synthesis; the exploration tokens live and
die in the sub-agent.

Requires `claude-agent-sdk` and a working OAuth token (either
$CLAUDE_CODE_OAUTH_TOKEN or an active Claude Code login).
"""

from memory_graph.orchestration.compact import compact
from memory_graph.orchestration.operator import (
    OPERATOR_DIRNAME,
    OPERATOR_FILE,
    read_operator_context,
    write_operator_context,
)
from memory_graph.orchestration.remember import remember
from memory_graph.orchestration.retrieve import retrieve

__all__ = [
    "OPERATOR_DIRNAME",
    "OPERATOR_FILE",
    "compact",
    "read_operator_context",
    "remember",
    "retrieve",
    "write_operator_context",
]
