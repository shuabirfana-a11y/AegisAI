# PoC 情报前端对接

## 已实现接口

`GET /api/v1/intelligence/vulnerabilities/{id}/poc?offset=0&limit=20`

- id 支持已有漏洞 UUID 或数据库中的规范漏洞编号；不存在返回 404。
- offset >= 0，limit 1–100；非法参数返回 422。该公共接口只读，不读取企业资产。
- POST 不支持，返回 405。没有下载、运行代码或扫描目标的接口。
- TypeScript：frontend/contracts/poc.ts 直接导出实际 OpenAPI 类型。
- 客户端：IntelligenceApiClient.poc(id, offset, limit)；baseUrl 使用队友配置的后端地址。
- 完整交接包 contracts/poc.ts、contracts/intelligence.ts 和 api/reference/intelligence-http.* 已同步。

## 展示规则

| 状态 | 展示含义 |
|---|---|
| NO_EVIDENCE | 当前库存未发现符合来源/证据要求的有效候选；同时展示 search_status 与 warnings |
| POC_CANDIDATE | 存在候选代码/仓库/材料，利用有效性没有确认 |
| VERIFIED_EXPLOIT | 当前关联核验、可用性状态和人工验证依据共同满足严格读取条件 |

空结果以 status=NO_EVIDENCE、items=[] 表示，不制造没有证据的 PoC Artifact。
association_status 是原候选关联状态，不能当作利用有效性状态。
verified_time 仅在 VERIFIED_EXPLOIT 时填写；缺失 language/description 为 null，不能猜语言或补描述。

每项 evidence_ref 都在该项 evidence 中解析；Evidence 包含来源、原文短片段、Raw/Observation ID、摘要及检索时间。
verification 是已存储核验结果，current_revision 区分当前与历史修订；不能把旧的 CONFIRMED 标记当作当前确认。
supports_exploit_validation 仅说明这一条证据满足读取验证依据的条件，仍必须结合关联状态和人工核验结果。

total 是全体有效候选数，status 不随当前分页改变。
stored_count 不包含已被现有规则拒绝的候选；omitted_count 表示缺少/损坏来源等而无法形成 Artifact 的记录数。
每个 Artifact 的证据与核验历史最多各 128 条，优先保留当前及真正验证依据。
omitted_evidence_count、omitted_verification_count、excluded_evidence_count 必须作为“历史/无效证据未全部显示”的提示；
底层历史数据保留。

## 数据与安全边界

1. 标题、描述、证据片段属于不可信外部文本，使用普通文本渲染，不能作为 HTML 或脚本执行。
2. 引用链接检查语法、公网地址形式和凭据参数；GET 不访问链接，所以不声称远程页面此刻仍可用。
3. 真实读取回执见 live-read-receipt.json：此前采集的 2 条活动候选，都是 POC_CANDIDATE/PENDING，没有实际利用验证。
4. 自动化测试使用合成来源；其中 VERIFIED_EXPLOIT 的正例是人工验证记录的合成夹具，不是真实漏洞利用成果。
5. 原有漏洞详情的原始 pocs 字段保持兼容；其 poc_status/poc_search_status 已和新接口采用同一读取规则。
6. 搜索失败、未运行或部分完成时，不把 NO_EVIDENCE 展示成“没有公开 PoC”或“资产安全”。

## 核验链复用

原流程保留：PocEnricher → Claim/Evidence → 原 VerificationService → 原始情报工具 → Investigation Agent →
原 EvidenceVerificationAgent / Tool Gateway → 原 Risk/Gate。

新 Artifact 是已有记录的标准化快照，不是第二套核验器。富化任务在原规则核验后保存 poc_snapshot；
查询读取当前记录，不触发模型、核验写入或攻击行为。
