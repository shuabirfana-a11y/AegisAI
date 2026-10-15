# 多资产调查 API 接入说明（Phase 14-B4）

本版支持**一个已入库的明确 CVE＋显式选择的资产 UUID 列表**。后端串行复用单资产调查链，不启动扫描、不执行 PoC、不修改资产。库存为声明信息，不能称为已扫描验证的部署。

依赖 PR #27 的 Phase 14-B3 代码；本功能尚未合并到 main。准确类型以 `docs/frontend-contracts/investigation-http.openapi.json`、`investigation-http.d.ts` 为准。原八个单资产接口保持兼容。

## 1. 真实接口

| 方法 | 路径 | 响应 |
|---|---|---|
| POST | `/api/investigations/batches` | 202，`BatchResponse`；附 `Location`、`Retry-After: 1` |
| GET | `/api/investigations/batches/{id}` | 200，进度、逐资产结果和汇总 |
| GET | `/api/investigations/batches/{id}/summary` | 200，仍为完整 `BatchResponse`，保留原证据引用 |
| POST | `/api/investigations/batches/{id}/cancel` | 200，取消请求后的实际状态 |

复用现有 Bearer 认证和服务端资产 owner。前端同源代理已放行以上两个 POST，不放行其他写操作；原跨源写入检查保留。凭据仅在服务器配置，不能写入浏览器代码。

这是可信内部调用边界下的 owner 隔离，**不是完整多用户／多租户认证系统**。同一服务令牌的调用方共享服务端身份。读取批次会重新校验资产访问范围、子调查身份和证据绑定；不得将任意 Run ID 拼进其他批次。

## 2. 提交

以下是真实双资产演示使用的请求结构；UUID 仅属于隔离演示库，不能复制到其他数据库后直接运行。

```json
{
  "vulnerability_id": "CVE-2025-47277",
  "asset_ids": [
    "de125dff-d8ba-4e73-af5d-51a9547334c6",
    "f2a175a4-b8f3-4303-94bc-accc52478a32"
  ],
  "timeout_seconds": 900,
  "child_timeout_seconds": 300,
  "idempotency_key": "demo-cve-2025-47277-batch-01"
}
```

也可用 `Idempotency-Key` 请求头；与请求体同时提供时必须一致。键长 1–150，不允许空白。字段不接受风险等级、可信状态、工具权限或自定义子调查；多余字段被拒绝。

- 漏洞必须已持久化为明确 CVE；也接受其数据库 UUID，解析后统一为 CVE。未入库返回 404，非 CVE 目标返回 422。
- `asset_ids` 必须显式提供；不支持“全部资产”或自动枚举。传输最多 100 项，去重后的业务上限默认 5，`AEGIS_BATCH_MAX_ASSETS` 可配置为 1–20。超过上限拒绝整批，不静默截断。
- 每资产快照最多 100 个活动组件。匹配组件不唯一、版本缺失或身份资料不足时，该项 `NEED_CONTEXT`，其他合法项继续。
- 批次总预算默认 900 秒、最大 1500 秒；子调查默认／最大 300 秒，实际不超过批次剩余时间。
- 单实例资源保护：全库同时只允许一个活动批次；未确认停止的子调查也占用该名额。现有单资产资源限制仍生效。

## 3. 读取字段与展示

`BatchResponse` 的完整字段由生成类型定义；以下为前端需要的映射。

| 字段 | 用途 |
|---|---|
| `batch_id / vulnerability_id` | 批次和唯一目标 CVE |
| `execution_status / revision` | 执行进度、响应版本；不表示所有资产安全 |
| `model_provider / model_name / execution_mode` | 显示 MOCK 或 REAL；REAL 本身不证明答案正确 |
| `created_at / updated_at / deadline_at / finished_at` | 时间与总截止时间，UTC RFC3339 |
| `reused / duplicate_asset_count / warnings` | 幂等复用、去重提示和限制 |
| `cancel_requested_at / cancellation_observed / recovery_required` | 取消与恢复事实，不能仅凭 CANCELLED 显示“模型已停止” |
| `items[]` | 一项对应一个请求资产，不能只显示成功项 |
| `summary.counts` | 覆盖统计；不能当作通过率或准确率 |
| `summary.actionable_asset_ids` | 已确认受影响、可按已有优先级处置的资产 |
| `summary.unaffected_asset_ids` | 有证据支持的限定不受影响结论 |
| `summary.unresolved_asset_ids` | 缺信息、冲突、失败、未执行或其他不能接受的结论，单列展示 |

每个 `items[]`：

| 字段 | 用途 |
|---|---|
| `snapshot` | 资产名、ID、环境、暴露、组件身份、部署版本、库存修订、快照时间和哈希；`is_demo` 必须显示 |
| `snapshot.provenance` | 固定 `USER_INVENTORY_NOT_SCANNED`，声明库存不是扫描证明 |
| `relations` | B3 候选节点／边引用、截断和警告；关联路径不是影响证据 |
| `execution_status / error_code` | 子任务是否执行、是否缺上下文或失败 |
| `impact / verification_status / risk_level / priority / gate_status` | 保留各自维度，禁止推导一个整体 PASS |
| `investigation_id / planner_run_id` | 打开原单资产调查／Trace 的关联入口 |
| `artifact_references / integration_result_id / answer_id` | 原 Artifact、Gate、AnswerEnvelope 引用 |
| `evidence_ids / claim_ids / citations / evidence_observations` | 原证据和来源引用，包括反证，不是自由生成的引用 |
| `recommended_actions` | 只包含原链已接受的处置建议；没有确认修复版本时不能补写版本 |
| `missing_fields / unresolved_items / warnings` | 需要用户补充或复核的信息 |
| `snapshot_valid / evaluation_time` | 本轮快照是否得到确认、原风险评估时间 |
| `historical_snapshot / current_safety_evaluated` | 固定 true / false，表示保存的快照判断，不证明读取时最新库存安全 |

库存现有模型没有可复用的 criticality 字段，因此快照保留 `criticality: "unknown"`，不根据环境猜测业务重要性。

## 4. 两组状态必须分开

批次 `execution_status`：`QUEUED / RUNNING / CANCEL_REQUESTED / COMPLETED / CANCELLED / TIMED_OUT / FAILED`。其中 COMPLETED 只说明处理循环结束，仍可能有失败或需补充项。

逐资产 `execution_status`：

| 状态 | 建议中文 | 展示规则 |
|---|---|---|
| NOT_STARTED | 等待执行 | 未检查，不能显示安全 |
| RUNNING | 调查中／停止待确认 | 取消之后仍可能处于此状态 |
| COMPLETED | 调查结束 | 继续读取该项 Gate 和业务判断 |
| NEED_CONTEXT | 需要补充信息 | 展示 missing_fields／库存变化原因，不显示“调查已成功” |
| FAILED | 调查失败 | 保留已产生的引用，不能归为未受影响 |
| NOT_EXECUTED | 未执行 | 取消／截止时间阻止启动，不能归为已检查 |

业务判断：`impact = AFFECTED / NOT_AFFECTED / UNKNOWN`；风险和优先级沿用旧契约（含 UNKNOWN、REVIEW_REQUIRED、DEFER），Gate 沿用 `PASS / PASS_WITH_WARNINGS / REPLAN_REQUIRED / HUMAN_REVIEW_REQUIRED / FAILED`，未产生时为 null。

处置列表仅接受：COMPLETED、快照有效、子 Gate 允许、核验 CONFIRMED、有证据、影响 AFFECTED、风险已知且已有 P0–P3 优先级。按原优先级后按资产 UUID 排序。不受影响列表也要求确认、证据和允许的子 Gate。其他全部进入 unresolved，不能排在 LOW 后面冒充更安全。

## 5. 脱敏结果节选

以下来自本轮真实本地 Qwen HTTP 演示，**只是字段节选，不是完整 BatchResponse 测试夹具**。

```json
{
  "batch_id": "791798cd-06c8-41bc-b247-9ba8f43b2dba",
  "vulnerability_id": "CVE-2025-47277",
  "execution_status": "COMPLETED",
  "execution_mode": "REAL",
  "items": [
    {
      "snapshot": {"asset_name": "Demo inference A", "is_demo": true},
      "investigation_id": "c1c34106-e080-4038-9e4c-6679ed675460",
      "impact": "AFFECTED", "risk_level": "HIGH", "priority": "P1",
      "verification_status": "CONFIRMED", "gate_status": "PASS"
    },
    {
      "snapshot": {"asset_name": "Demo inference B", "is_demo": true},
      "investigation_id": "b824f465-6fa8-4d18-9f4d-9de207195183",
      "impact": "NOT_AFFECTED", "risk_level": "LOW", "priority": "DEFER",
      "verification_status": "CONFIRMED", "gate_status": "PASS"
    }
  ]
}
```

A 为 vLLM 0.6.5，B 为 0.8.5；依据保存的官方公告快照，不是现场扫描或实时公告抓取。完整的脱敏决策／引用记录见 `docs/phase14b4/real-demo.json`，该文件也为节选记录。

## 6. 幂等、取消、轮询与恢复

- 相同 owner、键、规范化漏洞、去重资产集合及预算：返回已保存批次，`reused=true`，不重复调用模型。资产顺序、重复资产、CVE 大小写和同漏洞 UUID 别名不改变请求身份。
- 同键改变漏洞、资产集合或预算：409。换库存／版本后需要重查，使用新键；旧键仍返回旧快照。
- 创建后按 `Location` 每 1–2 秒轮询 GET；离开页面取消本地请求，切换批次使用 AbortController 或 requestId 防旧响应覆盖。`revision` 只用于同批响应排序。
- 取消不会删除已有结果。之后不再接纳新子调查；活动项转发旧单资产取消。`cancel_requested_at` 代表已请求，`cancellation_observed` 才表示本批没有仍标记 RUNNING 的子项。外部模型调用可能尚未返回。
- 取消／超时宽限结束后，批次可能已经 CANCELLED／TIMED_OUT，而子项仍 RUNNING，此时 `recovery_required=true`。继续 GET 会只对已经接纳的子调查回读和对账，不启动新调查或模型调用。
- 进程重启不自动重放批次。超过 90 秒没有心跳会提示 `WORKER_HEARTBEAT_STALE_NO_AUTOMATIC_REPLAY`；由维护人员查看原单资产状态并决定恢复。新建键不能绕过仍在活动的子调查。

## 7. 错误处理

与旧接口一致，错误响应为 `{error_code, message, request_id, retryable}`；不会返回内部堆栈。422 输入错误的具体结构仍以 OpenAPI 为准。

| HTTP／代码 | 处理 |
|---|---|
| 401 / 403 | 认证缺失／失败；不要轮询重试 |
| 404 | 目标或资产不存在、无权读取；不猜测其他 ID |
| 409 `IDEMPOTENCY_CONFLICT` | 同键请求不同；确认范围后使用新键 |
| 422 `ASSET_LIMIT_EXCEEDED` / `INVENTORY_LIMIT` / `TARGET_SCOPE_UNSUPPORTED` | 缩小显式范围或补齐入库资料 |
| 422 `IDEMPOTENCY_KEY_REQUIRED` / `IDEMPOTENCY_KEY_MISMATCH` / `INVALID_IDEMPOTENCY_KEY` | 修正键 |
| 429 `BATCH_BUSY` | 已有批次或未确认停止的子调查；读取原批次，不循环创建 |
| 500 | 引用、完整性或系统异常，保留 request_id 交维护人员；不能显示为无风险 |
| 503 `SERVICE_UNAVAILABLE` | 服务正在关闭，按 retryable 提示处理 |

子项还可能保留 `CREATION_ACK_TIMEOUT`、`CHILD_CREATION_UNCERTAIN`、`CHILD_RESULT_UNAVAILABLE`、`INVENTORY_CHANGED_*` 等原因；请求 ACK 超时不代表调查没有创建。创建前字段不满足原单资产输入约束时为 `NEED_CONTEXT / CHILD_INPUT_INCOMPATIBLE`，`missing_fields=["component_input"]`，需修正库存记录后用新键重试；创建前准备异常为 `FAILED / CHILD_PREPARATION_FAILED`。这两类确定未启动子调查，不会保留虚假的 RUNNING。

## 8. TypeScript 与页面接入

`frontend/contracts/investigations.ts` 已增加 `BatchRequest / BatchResponse` 映射和 `createBatch / batch / batchSummary / cancelBatch`。可直接使用客户端，或使用生成的 `investigation-http.d.ts`。本轮未修改 UI。

页面建议依次展示：范围与快照 → 覆盖进度 → 逐资产结果 → 已确认处置清单 → 待补充／复核清单。所有跳转均使用该项返回的子调查及证据引用，不根据 CVE 给不同资产共享风险卡片。
