# Phase 9 frontend skeleton

Status: **PARTIAL pending real backend integration**. The independent frontend starts and its functional skeleton is verified. Backend port 8000 was unavailable during the frontend runtime check; fixture results below do not establish real Agent/database integration.

## Scope and architecture

The implementation is under `frontend/`. It uses browser ES modules, small page modules, a memory session, an API service, and Node's built-in HTTP server. No product dependencies were added. The existing Phase 4 prototype and its port 8768 are untouched. The new frontend listens only on `127.0.0.1:8769` and proxies to fixed `127.0.0.1:8000`.

This stage implements page structure, data flow and ordinary text/form/table controls. The stylesheet only supplies readable spacing, wrapping and borders. There are no animations, visual effects, brand assets or formal UI design.

## Routes and live API bindings

| Route | API/data |
|---|---|
| `/dashboard` | `/health`, vulnerability count/coverage, protected asset overview, review count |
| `/vulnerabilities` | `GET /api/v1/vulnerabilities?limit=20`, optional identifier search |
| `/vulnerabilities/:id` | Actual vulnerability detail, source assertions, claims, evidence, POC/Patch candidates, conflicts and reviews |
| `/assets` | Protected asset list/overview; selected asset's `/risks?limit=20` |
| `/reviews` | Existing read-only `/api/v1/reviews?limit=20` |
| `/assistant` | Protected query submission, run/tasks/trace reads, evidence expansion, related links and warnings |
| `/system` | Health and actual source synchronization/coverage fields |

All list and evidence views use actual API responses. Runtime code installs no sample records and supplies no fabricated success fallback. A malformed list without `items` is an explicit schema error. Dates are shown as database strings. Unknown values, PENDING/CONFLICT, stale snapshots, demo inventory flags, source limits and missing confirmation remain visible.

The existing `/reviews` read endpoint intentionally excludes `ASSET_MATCH_REVIEW`; that backend distinction is explained in the skeleton. The frontend does not implement review decisions or inventory mutation.

## Assistant contract

The query form sends `{question, asset_id?, target?, mode, request_key, realtime:false}`. Each new submission gets a UUID request key; an explicit retry after network/server failure reuses its original payload/key. The backend controls ownership.

The page supports all eight requested states: PLANNING, RUNNING, WAITING_TOOL, VERIFYING, REPLANNING, WAITING_REVIEW, COMPLETED and FAILED. Active runs are polled every two seconds, up to 90 polls per page action. WAITING_REVIEW stops automatic polling. Manual refresh and loading an existing Run UUID are available. Navigating away aborts page reads; the run ID survives navigation in memory. Changing or clearing the token resets it.

Result, evidence references, related vulnerabilities, related assets and warnings are separate sections. Structured result fields remain expandable so incomplete or evolving contracts are visible. Evidence UUIDs can be expanded through the existing evidence endpoint. Task trace is limited to explicit audit summary fields; internal reasoning fields are excluded. SSE is not implemented and is not required by the Phase 9 request.

## Access and local proxy boundaries

Users manually enter `AEGIS_ASSET_TOKEN` in a password field. The value stays in a closure in page memory, is cleared from the field after submission, is never placed in URL/storage/logs, and disappears on reload. No token is embedded or injected by the frontend server.

Protected calls attach the supplied Bearer header. The local proxy forwards Authorization while excluding browser Cookies and backend Set-Cookie headers. It accepts only local Host values, fixed API/health paths and a fixed upstream. Only Assistant query submission is writable; it requires a matching Origin and JSON content type. Body size is bounded at 2 MiB and upstream requests time out. Static content is confined to `frontend/public/` with no arbitrary proxy URL feature. External text is rendered with `textContent`; the server applies a same-origin CSP.

## Verification

**Node built-in tests: 19 passed, 0 failed, 0 skipped.** Tests exercise the real router/service/proxy with temporary local HTTP fixture servers: required routes, malformed paths, memory auth, token header forwarding, missing auth, API JSON/schema errors, HTTP 409, absolute URL rejection, status normalization, static deep links, cookie exclusion, same-origin writes, unavailable upstream and oversized body handling. The finalized backend contract added tests for the 2000-character question limit, tool sequence/attempt/output status and event timestamps without hidden reasoning fields. Initial tests failed before implementation; later regression tests failed before their fixes.

- `work/phase9_frontend_red.log`: initial 14 failing tests against feature stubs.
- `work/phase9_frontend_regression_red.log`: reproduced list schema omission and oversized-body double response.
- `work/phase9_frontend_integration_red.log`: reproduced finalized backend contract gaps.
- `work/phase9_frontend_tests.log`: final 19 passing Node tests.

**Playwright browser request-fixture checks: 35 passed.** These checks are explicitly fixture-only: seven routes, literal external HTML, original dates, empty review response, asset/vulnerability conflicts, all eight Agent states, query payload shape, evidence expansion, no internal reasoning display, warnings, HTTP 409, memory-only token and clearing on reload.

- `work/phase9_frontend_browser_fixture.js` / `.log`: repeatable fixture-only browser checks.
- `work/phase9_frontend_assistant_fixture.png`: visual confirmation of the minimal Assistant structure, clearly containing fixture data.
- `work/phase9_frontend_browser_runtime.js` / `.log`: unmocked static/proxy route checks and actual backend availability.
- `work/phase9_frontend_runtime.png`: unmocked frontend availability/error view.

The frontend server is actually started; the live UI reports upstream unavailable rather than replacing data. All seven direct URLs serve successfully and missing-token submission is blocked. Real protected asset/Assistant runs and evidence reads need the orchestrator to start the configured backend and perform the authorized real integration check. No Dify or database changes were made by this frontend task.

## Prepared real integration check (2026-10-06)

`work/phase9_frontend_real.js` is a standalone Node/Playwright check with no request mocks. The root runtime helper supplies `AEGIS_ASSET_TOKEN` through the child environment; the script enters it into the password field and never writes or prints its value. The runner writes `work/phase9_frontend_real.json` and `work/phase9_frontend_real.png` after seven routes, actual owner assets/demo flags/risks/reviews/sources, an actual pending Fast request for CVE-2026-64849, a Deep conflict investigation of CVE-2026-57173, tasks/trace/evidence expansion and reload clearing. It asserts human review for the conflict case rather than labeling it a confirmed answer. Until that script is run against the configured backend, this is prepared verification only.

The CLI's `run-code` VM cannot access `process`/`require` and rejects dynamic imports, so the real runner uses the already-installed Playwright package and Chromium directly. Browser launch was verified with `--check-runtime`; that flag performs no backend or credential check. No package or browser installation was needed.

## Run

```powershell
& 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' frontend/server.mjs
& 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' --test frontend/tests/*.test.mjs
```

Open `http://127.0.0.1:8769/dashboard`. The server forwards APIs to port 8000 and does not launch a backend, expose its configured secret, or modify the database.


## 实际联调更新（2026-10-06）

当前骨架验收PASS：19 Node测试、41无mock真实Backend浏览器检查、七个路由。JSON证据 frontend_browser_results.json。已统一前端输入2000字并显示tool sequence/attempt/events；tasks逐项运行状态仍pending，列为Minor。Token只在内存，本轮验证不交付共享密码。


## 本次续作更新

tasks API已展示最新执行事件，started映射running，最终Artifact可覆盖已执行但被拒的状态。三个真实Deep样例捕获running；41浏览器检查通过。
