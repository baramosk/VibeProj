"""PostToolUse 훅: Claude가 수정한 .py 파일을 black으로 정렬한다."""

import json
import subprocess
import sys

data = json.load(sys.stdin)
path = data.get("tool_input", {}).get("file_path", "")
if path.endswith(".py"):
    subprocess.run([sys.executable, "-m", "black", "-q", path], check=True)
