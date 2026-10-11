# AegisAI frontend skeleton and local proxy

This independent frontend uses browser ES modules and Node's built-in HTTP server. It adds no dependencies or formal visual design.

Run from the repository root with an available Node runtime:

```powershell
& 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' frontend/server.mjs
```

Open `http://127.0.0.1:8769/dashboard`. The existing prototype on port 8768 is separate. Start the existing backend on `127.0.0.1:8000` using the project backend instructions. The frontend does not start or change the database.

Protected APIs require the backend-configured `AEGIS_ASSET_TOKEN`; the backend controls the owner. With a separately started proxy, enter your own token in the password field: it stays in browser memory and disappears on reload. The existing `scripts/start-local-demo.ps1` instead creates an ephemeral token and supplies it to both local service processes; in that explicit local mode the proxy injects it server-side and `/client-config` reports `localDemoAccess`, without returning the token to the browser. That launcher depends on this developer machine's PostgreSQL cache.

Routes: `/dashboard`, `/vulnerabilities`, `/vulnerabilities/:id`, `/assets`, `/reviews`, `/assistant`, `/system`.

The proxy forwards `/api/v1/*`, the eight `/api/investigations` operations and `/health` to the fixed loopback backend. It excludes browser cookies and enforces same-origin JSON requests on its exact write allowlist: Assistant submission, investigation creation and cancellation. Other existing writes remain blocked. Of 42 backend operations, 35 are available through this proxy and 7 writes remain blocked.

The seven existing pages still use the earlier Assistant workflow. A Phase 11-D investigation workbench is a teammate frontend task; adding proxy support does not add that UI or convert the old response into AnswerEnvelope. Use the exported TypeScript client and [HTTP contract](../docs/PHASE12B_INVESTIGATION_API.md). Poll investigation status about once per second, fetch trace/artifacts when `revision` changes, and stop on terminal states. No SSE/WebSocket API exists.

Default Mock has no PlannerPlan fixture and therefore cannot plan an arbitrary investigation. See [backend demo checks](../docs/BACKEND_DEMO_STABILITY.md) for the explicit separation between transport readiness, a controlled synthetic offline chain and a real model run.

Node built-in tests use real temporary local HTTP servers for protocol behavior; those fixture tests are not evidence of backend or database integration:

```powershell
& 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' --test frontend/tests/*.test.mjs
```

Data dates and states are displayed as returned. No sample records are installed. Missing data, auth failures, conflicts and backend errors are visible. Task trace displays allowlisted audit summary fields, not internal model reasoning.
