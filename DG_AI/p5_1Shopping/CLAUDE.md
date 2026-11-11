# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run server: `python main.py --port 8000` → open `http://127.0.0.1:8000` (the server serves the page and the API together).
- Tests: `python -m unittest discover -s tests -v`
- Also verify on Python 3.13 when possible: `C:\Python313\python.exe -m unittest discover -s tests`

## Constraints
- Standard library only. Do not add third-party packages.
- Keep code compatible with Python 3.9. Do not use `match` statements, parenthesized context managers, or other 3.10+ syntax. `from __future__ import annotations` is already used for `X | None` hints.
- Do not use `cgi`; it was removed in Python 3.13. Multipart parsing lives in `minishop/multipart.py`.
- All store state is in memory behind `threading.RLock`. Any new mutation must take the lock.

## Architecture
- `minishop/store.py`: domain logic and file storage. Raise `ShopError(status, message)` for client errors.
- `minishop/server.py`: `ThreadingHTTPServer` handler and routing. Frontend and API are served from the same origin, so `fetch` uses relative paths.
- `minishop/static/index.html`: the single-page frontend. Escape all dynamic values with `esc()` before inserting them into the DOM.
- Auth is a Bearer token issued by `POST /api/users`. It is a demo token, not a session system.

## Gotchas
- Do not open the page with VS Code Go Live (port 5500). It serves static files only, so every `/api` call fails. Use port 8000.
- Profile photo uploads: only `.png`, `.jpg`, `.jpeg`. Dangerous extensions (`.exe`, `.bat`, `.js`, `.html`, etc.) return 400 with "위험한 확장자". The file content must also be PNG or JPEG magic bytes. Max file size is 5MB, and the request body is capped at 5MB + 16KB overhead.
- Filename collisions never overwrite. The code opens with `"xb"` and appends `_<timestamp>` to the stem. Keep this behavior.
- `uploads/` holds user data at runtime. Do not commit it or read its contents into context.
- Do not add CORS headers until the frontend and backend are deliberately split. Same-origin is currently required.
