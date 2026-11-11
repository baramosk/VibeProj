---
name: verify
description: Run the minishop unit and HTTP test suite and report the result. Use after changing any code in this project.
---

Verify the current changes in this project.

1. From the project root, run `python -m unittest discover -s tests -v`.
2. If Python 3.13 exists at `C:\Python313\python.exe`, run the same suite with it too.
3. Report the number of tests run and the pass/fail counts.
4. If anything fails, show each failing test name and its traceback. Do not claim success unless the run ends with `OK`.
5. Remove `__pycache__` folders afterward with `rm -rf minishop/__pycache__ tests/__pycache__ .claude/hooks/__pycache__`.
