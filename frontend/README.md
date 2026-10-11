# Phase 9 frontend skeleton

This independent frontend uses browser ES modules and Node's built-in HTTP server. It adds no dependencies or formal visual design.

Run from the repository root with an available Node runtime:

```powershell
& 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' frontend/server.mjs
```

Open `http://127.0.0.1:8769/dashboard`. The existing prototype on port 8768 is separate. Start the existing backend on `127.0.0.1:8000` using the project backend instructions. The frontend does not start or change the database.

The asset and Assistant pages require the backend-configured `AEGIS_ASSET_TOKEN`. Enter it manually in the password field. It stays in memory, is removed from the field after submission, and disappears on reload. The server does not read or inject that token. The backend controls the owner.

Routes: `/dashboard`, `/vulnerabilities`, `/vulnerabilities/:id`, `/assets`, `/reviews`, `/assistant`, `/system`.

The local proxy forwards only `/api/v1/*` and `/health` to the fixed loopback backend, forwards the supplied Authorization header, excludes browser cookies, and rejects writes unless their Origin matches the frontend. The skeleton only exposes Assistant query submission as a write operation. No SSE is required; Assistant uses bounded 2-second polling with manual resume.

Node built-in tests use real temporary local HTTP servers for protocol behavior; those fixture tests are not evidence of backend or database integration:

```powershell
& 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' --test frontend/tests/*.test.mjs
```

Data dates and states are displayed as returned. No sample records are installed. Missing data, auth failures, conflicts and backend errors are visible. Task trace displays allowlisted audit summary fields, not internal model reasoning.
