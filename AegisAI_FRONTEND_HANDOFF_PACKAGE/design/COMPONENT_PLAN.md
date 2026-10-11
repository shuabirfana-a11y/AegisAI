# 组件计划与类型边界

组件名称是团队实现建议，不表示当前仓库已经有同名组件。优先复用现有页面/控件，将数据源隔离在适配层。

| 组件 | 输入/数据来源 | 职责与限制 |
|---|---|---|
| AppShell / PageHeader | 路由、权限、数据模式 | 六主导航、七页入口；Mock 标签不隐藏 |
| DataStatePanel | loading/error/empty/stale/partial 等页面状态 | 保留输入/快照，未知不是成功 |
| VulnerabilityTable | VulnerabilityListResponse | 身份/日期/来源与现有列表字段；未提供富化列不凭空补造 |
| VulnerabilitySections | VulnerabilityDetail | 版本、CVSS/CWE、Claim、候选、冲突和时间线 |
| ClaimPanel | HttpClaim 或专业 Claim/VerifiedFact，分开适配 | HTTP value_json 与快照 value 不混用；显示作用范围/核验结果 |
| EvidenceDrawer | HttpEvidence 或 EvidenceReference/EvidenceObservation | 来源标识/定位/哈希；派生 ID 不默认能请求 UUID 接口 |
| AssetRiskTable | CurrentAssetRisk / HistoricalAssetRisk | 三态匹配、时间/版本/快照、证据；区别用户库存和扫描 |
| ReviewWorkbench | ReviewDetail | 对照证据、保留草稿；当前提交被代理拦截 |
| InvestigationForm | InvestigationRequest；旧问答另用 QueryRequest | 保留请求 key 与范围；完整新入口尚未开放 |
| InvestigationProgress | InvestigationStatus | 四层状态分开，不显示臆测百分比；revision 防乱序 |
| AgentExecutionPanel | InvestigationTrace / AgentTrace | run、task_statuses、tool_calls、Artifact 引用，按真实回执展示 |
| TaskRunPanel | RuntimeTaskTrace / AgentRunTrace | 专业任务级数据；不能把旧 LegacyTaskRun 强制转成新类型 |
| GateResultPanel | IntegrationResult，或仅状态的明确展示投影 | status、checks、blocking_issues、warnings、objective_coverage |
| AnswerPanel | AnswerEnvelope | 已确认/争议 Claim、风险、处置、引用、范围与快照时间 |
| RiskSummary | Answer RiskView 或 RiskAnalysisArtifact，分开适配 | affected=null 保持未知；priority 和 confidence 解释准确 |
| SourceStatusTable | SourcesResponse / SyncRunsResponse / Health | planned/deferred/错误区分，运行时长与时间口径不造数 |

## 数据适配要求

1. 现有 HTTP、Phase 11-D 内部 DTO、旧问答 DTO 和 Mock 包装四者分离。Mock 适配器负责取 `.scenarios[name]`，不把元数据当业务字段。
2. TypeScript 类型从 `contracts/` 引入，不在组件中再手抄一套状态枚举；JSON 字段在边界做运行时校验。`unknown` 先收窄再显示。
3. 组件不计算版本是否受影响、核验证据是否充分、风险分数或 Gate 是否通过；这些是后端结果。没有结果就显示缺失/待提供。
4. 派生证据在抽屉展示快照引用；只有明确数据库 UUID 并且当前 HTTP 可读时才请求 `/api/v1/evidence/{id}`。
5. 根调查 ID、专业 run/task/artifact 引用和 integration_id 分开缓存。不得把独立 Gate 示例混入 PASS 回执。

## 实施顺序

先做字段准确的漏洞详情与 Evidence 抽屉 → 中心/总览/系统数据读取 → 授权资产/复核读取 → 完整调查结果的 Mock 组件与异常状态 → Phase 12-B 后真实生命周期联调。旧页面先复用，缺失协议先记录，不重新开发已有能力。
