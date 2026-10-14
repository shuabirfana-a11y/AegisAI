# Phase 14-C.1：前端联调问题修复与演示稳定化

日期：2026-10-14。项目：AegisAI，ICT 命题九。

## 1. 完成范围与版本

在独立分支 `codex/phase14c1-frontend-integration-fixes` 完成三项前端修复。后端基线为 `4f6722800fa60a0264356b0c4ce6ade69cd36073`，前端上传版本为 PR #23 的 `e982b400e374318399f77d7a06bbcfe53fc3b80f`。保留其页面和交互设计，保留后端更新过的生成契约。

没有修改 `backend/app/`、数据库迁移、Planner、Runtime、专业 Agent、Verification、Risk 或 Gate 业务规则。没有合并 PR #23，也没有版本冻结。

## 2. 三个问题根因与修复

| 问题 | 根因 | 修复 |
| --- | --- | --- |
| 漏洞详情报错 | 调用 `fields()` 却未导入；null 行、非数组字段及请求异常没有完整防护 | 恢复导入，统一 LOADING / SUCCESS / WARNING / EMPTY / ERROR；空字段保留 UNKNOWN；错误就地展示；离开页面后不追加迟到结果 |
| 缺版本却显示受理 | 创建响应按成功回执处理，忽略后端 `NEED_CONTEXT` 联合类型 | 同步 TS 联合响应；先判断 NEED_CONTEXT，展示缺少的版本和资产信息；不保存调查 ID、不轮询、不显示受理 |
| 调查切换竞态 | 异步步骤使用可变全局调查 ID/客户端；旧响应和错误可写入新界面 | 每次切换/提交推进 epoch，取消旧请求，并固定客户端、调查 ID、signal；每次 await 后核对；旧 success/error/finally、历史及模式切换响应均不能覆盖当前页面 |

审查中一并修复：取消回执与轮询共用 revision 校验，旧取消版本不能覆盖较新终态；创建/status/Trace/Artifact/Answer 按各端点真实契约校验绑定；未知状态保留原文并暂停刷新，不假定完成。

真实联调发现 `IntegrationResponse.logical_investigation_id` 属于内部 Gate 上下文，不等于网页调查根 ID。前端通过已经绑定的 Trace / Answer 的 `integration_result_id` 核对 Gate 的 `integration_id`，保留内部 ID，拒绝不一致引用。没有改写后端响应或降低 Gate 标准。

## 3. 修改文件

直接修复：

- `frontend/public/modules/pages/vulnerabilities.js`
- `frontend/public/modules/pages/assistant.js`
- `frontend/contracts/investigations.ts`
- `docs/frontend-contracts/investigation-client.ts`
- `AegisAI_FRONTEND_HANDOFF_PACKAGE/api/reference/investigation-client.ts`

验证与工程支持：

- `frontend/tests/workbench-dom.test.mjs`：26 项新增 DOM 回归。
- `frontend/package.json`、`frontend/package-lock.json`：锁定开发测试依赖 jsdom 26.1.0，不进入浏览器运行依赖。
- `.github/workflows/ci.yml`：安装锁定的前端测试依赖。
- `backend/tests/orchestration/test_legacy_compat.py`、`docs/phase14c1/source_hash_exceptions.json`：仅将已授权修改的 12 个前端文件加入精确哈希例外，原冻结基线与后端约束不变。
- 本报告及 `docs/phase14c1/`：脱敏实跑记录、截图、验证说明。

此外，此修复分支包含 PR #23 已上传的页面、Mock 回放、浏览器 HTTP 客户端和本地代理变化；它们是前端集成基线，不是本次重新开发的功能。完整路径见 PR 文件列表。

## 4. 实际测试结果

| 检查 | 实际命令 | 结果 |
| --- | --- | --- |
| 原有及新增前端测试 | `node --test frontend/tests/*.test.mjs` | **67 passed，0 failed，0 skipped；原有 41 + 新增 26** |
| 后端便携回归 | `python scripts/ci/run_backend_tests.py` | **673 passed，1 deselected**；排除项为原配置要求的真实缓存 embedding 测试 |
| 前端语法 | `node scripts/ci/check_frontend.mjs` | 24 个 JS 文件通过；原生 JS 项目没有应用 build 脚本，build 为 NOT_APPLICABLE |
| TypeScript 契约 | `node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json` | 通过 |
| 调查 HTTP 导出 | `python scripts/export_investigation_api.py --check` | 10 个文件与实际代码一致 |
| 情报 HTTP 导出 | `python scripts/export_intelligence_api.py --check` | 7 个文件、8 个操作一致 |
| 工程故障门禁 | `python -m unittest discover -s tests/engineering -v` | 18 项通过 |

验证过程先证明原上传前端的 21 个回归有 20 失败、1 通过，再修复。独立审查发现的三个回归先 0/3，通过修复后通过；Gate 端点语义的两个回归先 0/2，通过修复后通过。最终以上 26 项新增测试全部通过。竞态测试明确模拟请求忽略 Abort 后仍迟到返回。

一条探索性命令运行整个 `test_legacy_compat.py` 时，2 个数据库测试因未配置专用测试库报 setup error，1 个源文件哈希检查通过；随后按本阶段范围运行精确哈希检查通过，便携回归通过。没有使用演示数据库跑破坏性测试。历史完整数据库回归的两项已知失败不属于本阶段，不能据此声称整个后端集成套件全绿。

## 5. 浏览器与真实模型演示验收

| 场景 | 实际结果 |
| --- | --- |
| 高风险调查 | 浏览器提交 → Qwen 本地真实 Planner → 三专业 Agent → Gate → Answer；`SUCCEEDED`、Gate `PASS`、Answer `COMPLETE`、风险 `HIGH / P1`，证据、Artifact 和建议已展示 |
| 缺版本/资产 | 显示 `NEED_CONTEXT`，分别要求版本和资产信息；`investigation_created=false`、`execution_mode=NOT_STARTED`；没有受理提示或调查 ID |
| 切换调查 | 快速由旧历史调查切换到新调查，最终状态/答案/Gate 保持新调查绑定；当前面板未包含旧根 ID |
| 漏洞详情 | 真实 `CVE-2025-47277` 详情返回 `SUCCESS`，CVSS/版本/Claim/Evidence 等记录可以读取，没有崩溃 |

本次新运行根 ID：`a583d1ae-ea72-45f6-92c7-85ef80879e65`。Planner run：`da4df65b-e4b8-4b9d-9d60-b77c9c0440e0`。Gate：`6b494cec-8129-4927-bb35-9922b3a17e94`。Answer：`b2ccac0a-f733-5e07-b0f1-373b219095c3`。

模型是 `openai_compatible / aegisai-qwen25-planner:latest`，通过本机 Ollama 调用。Answer 事实表达使用现有 `DETERMINISTIC_TEMPLATE`。沿用既有配置的 Gateway embedding provider 为 Mock，不把这一部分宣称为真实向量模型效果验证。

漏洞资料来自已有官方厂商/OSV 快照，获取时间为 2026-10-12；资产库存显式 `is_demo=true / USER_INVENTORY_NOT_SCANNED`，不是企业真实扫描结果。实跑不使用 Ground Truth，不进行业务准确率评分，也不把 Mock 回放作为真实调查。

实跑投影及浏览器记录见 `docs/phase14c1/`；原始响应、进程记录和临时凭据留在忽略目录 `work/phase14c1/private/`，不进入 Git 或交付包。

## 6. 接口一致性与停止点

八个调查 HTTP API 的 URL、方法、后端 Schema 均保持不变。前端创建响应现在准确支持 `InvestigationCreateResponse | ContextRequiredResponse`。status/cancel/Trace 的双根 ID、Artifact 的单根 ID、Answer 的网页根 ID、Gate 的引用绑定分别按真实语义检查。

保持 Mock 为显式 `MOCK_ONLY`，未知状态和证据不足状态不伪装成成功。来源中断、模型失败和 API 失败仍显示后端实际失败状态。本阶段完成后停在修复 PR 审查，不自动合并，不进入新功能、版本冻结、Word/PDF 或视频制作。
