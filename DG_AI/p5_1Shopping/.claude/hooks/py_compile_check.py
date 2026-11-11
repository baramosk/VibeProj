"""PostToolUse hook: edited .py files must at least compile.

Claude Code passes the tool call as JSON on stdin. Exit code 2 sends the
error text back to Claude so it can fix the file.
"""

import json
import py_compile
import sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path", "")
if not path.endswith(".py"):
    sys.exit(0)

try:
    py_compile.compile(path, doraise=True)
except py_compile.PyCompileError as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(2)
