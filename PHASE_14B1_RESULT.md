# Phase 14-B1：PoC 情报富化模块建设结果

## 1. 背景与范围

本阶段为 AegisAI 命题九完善公开 PoC 情报的结构化展示、证据关联和只读接口。
使用已有 GitHub 静态搜索/README 解析、候选表、Evidence、Claim、核验服务及专业 Agent；
没有新增扫描器、攻击能力或 Agent，没有修改 Planner、Runtime、Risk/Gate 核心规则。

## 2. 数据模型

新增冻结的 Pydantic POCArtifact：id、vulnerability_id、source、reference、title、description、language、
status、created_time、verified_time、evidence_ref。另含证据、核验记录、关联/可用性状态、历史裁剪计数。

id 沿用已有候选 ID；created_time 为 first_seen_at。语言仅取真实仓库 metadata，缺少则 null。
快照写入既有 EnrichmentJob.result.artifacts.poc_snapshot，不新增表或迁移。
API 当前投影以 as_of 标记读取时点，不覆盖历史 Evidence 或旧核验记录。

## 3. 状态定义

- NO_EVIDENCE：没有可形成有效 Artifact 的活动候选，返回空 items；必须结合搜索状态判断覆盖范围。
- POC_CANDIDATE：有可追溯候选，但没有满足有效利用确认依据。
- VERIFIED_EXPLOIT：原候选关联已确认、可用性 verified_usable、当前修订的可信人工核验，
  且实际链接的验证 Evidence 本身完整、当前、支持、时间有效、值一致。

核验关联 CONFIRMED、仓库名含 CVE、找到代码或独立引用，均不能独自变成 VERIFIED_EXPLOIT。
未来时间、旧修订、来源错配、冲突、过期/中性验证证据都会保持候选。
本模块没有执行任何 PoC；正例状态仅表示接受已存在并可追溯的人工验证依据。

## 4. Evidence 与 Verification 流程

PocEnricher 保留现有 Claim/Evidence 写入路径。README 格式异常时保留失败原文与错误，
使用搜索响应中的候选条目作为较弱 Evidence，任务保持 PARTIAL。
已有 VerificationService 完成原规则核验后增加快照投影；现有专业 Verification Agent 仍通过 Tool Gateway
读取原 Claim/Evidence，不依赖模型裁决利用有效性。

Artifact 强制 Evidence 引用可解析，核对 source/observation/raw 关系、摘要和片段定位。
无效候选被明确列为 omitted，不中断其他候选。公共接口不返回资产范围证据。
证据和核验历史各最多 128 条，保留真正的验证依据并报告裁剪数量；数据库历史不删除。

## 5. API 与前端变化

新增 GET /api/v1/intelligence/vulnerabilities/{id}/poc，支持 UUID/规范编号、分页、404/422/405。
返回 POCPage，包含汇总状态、搜索状态、Artifact、来源、Evidence、核验结果和限制。
只读 API 不调用模型、不获取远程链接、不改变核验结果。
原情报列表/详情的 PoC 汇总状态同步同一投影，原始 pocs 字段保持兼容。

实际 OpenAPI、TypeScript、客户端和前端交接包已同步；详见 docs/phase14b1/FRONTEND_POC_HANDOFF.md。

## 6. 修改文件

- 新增 enrichment/poc_schemas.py、poc_artifacts.py；已有 enrichment/service.py 添加原核验后的快照。
- 已有 enrichers/poc.py 保存语言，并对失败 README 采用搜索 Evidence。
- 已有 api/intelligence.py 增加只读路由；monitoring/views.py 对齐汇总状态。
- frontend/contracts/intelligence.ts 增加 poc 方法，poc.ts 导出实际类型。
- 两套实际 API/TypeScript 镜像、导出脚本、CI 单元入口、兼容性边界测试。
- 新增 PoC 模型/API/错误/边界测试、原专业核验链联调测试和本阶段文档。

业务受保护文件检查：634 个 Agent/Planner/Runtime/Orchestrator/Gate/Model Gateway/迁移/评测与实验文件未改。
冻结历史基线不重写；两处既有富化适配的授权摘要另行记录。

## 7. 实际验证记录

实际记录见 docs/phase14b1/test-summary.json。

| 检查 | 本次实际结果 |
|---|---|
| 新增 PoC 专项用例 | 35 项（34 项 DTO/API/边界 + 1 项原专业 Agent 链路） |
| 新增及相关回归 | 186 通过，0 失败，1 项 AnyIO 弃用警告 |
| 最终 portable backend baseline | 654 通过，1 个已有真实缓存 Embedding 测试明确排除，1 项弃用警告 |
| 全量后端回归 | 1574 通过，2 个既有失败，23 项已有警告 |
| 前端原有测试 | 23 通过 |
| 工程检查 | 18 通过 |
| 契约/类型/语法 | 48 个实际 HTTP operations、6 个情报 GET、导出一致；TypeScript 通过；17 个 JS 文件通过 |

全量运行在最后的审查边界修复之前启动；最后修复已由上述 186 项专项和最终 portable 回归验证，
不把这次全量结果宣称为最终代码全部绿色。
两项失败为 test_bench_http 的 unknown_version 和 test_failure_cancel 的 ambiguous；
它们在上一阶段基线已复现，是 Unknown Context 准入与旧测试预期的差异，不属于 PoC 修改。

- 实际专业核验链测试使用合成外部 HTTP 响应、真实 PostgreSQL、原工具网关/子进程/Agent。
- 真实 HTTP 只读验证：两条此前采集的活动候选均 POC_CANDIDATE，存储核验 PENDING。
- 本次真实读取中模型调用 0、利用执行 0、目标扫描 0；未把合成 VERIFIED 正例算成真实能力。
- 原始全量后端回归的已知 Unknown Context 两项失败另行报告，不修改核心业务去绕过。

## 8. 当前限制

没有真实人工验证的有效利用记录，所以不宣称任何真实 VERIFIED_EXPLOIT。
旧候选未保存语言时仍为 null；不会追加猜测。原搜索范围受 GitHub 可用性和现有条数上限约束。
URL 检查不代表实时链接可用；未增加持续监测调度或真实攻击验证。
历史原始 pocs 供旧客户端兼容，新客户端应使用 typed /poc 接口和 warnings。
本阶段工程测试不代表业务准确率或比赛得分；未运行正式 Benchmark。

## 9. 停止与下一阶段

完成 PoC Artifact、三态、Evidence、原 Verification 链复用、只读 API 和契约交接后停止。
未进入 Phase 14-B2 多源监测增强。
