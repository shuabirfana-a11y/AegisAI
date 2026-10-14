# Phase 14-B2：多源情报监测与自动化流水线结果

## 1. 完成内容

在原有11个采集适配器之上增加统一 CollectorRegistry/CollectorFramework、有界 IntelligencePipeline 和本机调度循环。
复用原 SyncService、FeedSyncService、Normalizer、EnrichmentService、VerificationService、KnowledgeIndex 和资产重算 worker。
未新增 Agent、采集平台、数据库迁移，未修改 Planner、Runtime、Risk/Gate 或评测规则。

调用链：选定来源 → 原采集/不可变 Raw → 原标准化 → 批次内富化 → 原 Claim/Evidence 核验 → 可查询情报/知识 → 原 Tool Gateway/Agent。
六类根富化任务包括 vendor、version、epss、kev、patch、poc。没有把论文链接、候选 PoC 或处理结束直接判成确认结果。

## 2. 数据源与覆盖

| 来源 | 接入方式与范围 | 本次实际网络结果 |
|---|---|---|
| CVE_LIST | 原过滤 Git 命名空间；新模式默认不自行初始化大库 | 未执行；无缓存时 DEFERRED |
| OSV、CISA_KEV | 原 HTTP/数据适配；保留原地址限制 | 未单独新增监测实跑；原 enrichment 使用对应能力 |
| NVD | 原声明 CVE 范围、有限原生记录 | PARTIAL，实际入库1条漏洞 |
| GHSA | 原 reviewed pip/公告窗口 | HTTPStatusError，FAILED 保留 |
| VENDOR_PYTORCH/VLLM/MLFLOW | 原三个固定官方 GitHub 仓库 | VLLM 本次失败；另外两个未实跑 |
| RSS_TRAIL_OF_BITS、RSS_GOOGLE_SECURITY | 原 RSS 元数据、片段、知识索引 | Trail of Bits 成功；Google 本次未实跑 |
| ARXIV | 原有界相关性查询、Atom 元数据/摘要 | ConnectError，FAILED 保留 |

五类来源的实际原适配器解析均通过合成 HTTP 测试，但这不能冒充五类网络来源同时在线。
GitHub/GHSA/厂商可能共享发布者；来源数量不等于独立证据数量。没有全量采集或“实时完整覆盖”结论。

## 3. 自动化和状态

新增配置限定记录量、目标量、根任务数、资产数、每轮启动工作截止时间和调度次数。
`--pipeline` 显式启用；未启用时原 CLI 保持兼容。定时循环遵守来源更新间隔，force 只作用首轮。
默认每轮执行6个根任务，显式0不执行。原富化服务产生的依赖任务单独统计，不暗称其受根任务预算约束。

流水线只处理选定来源捕获及同模式未完积压，保留原批次身份、采集状态、时间、错误与模式。
历史扫描有100次源运行的上限、按来源/模式保存的轮转游标；旧 RUNNING-only 任务不占可执行目标预算。
无关队列不被排空，关闭来源不被调度重新开启。PostgreSQL advisory lock 防止两个新 worker 同时运行。
旧全局 worker 未改，不能与新 worker 同时处理同一范围。

SyncRun.details 增加 pipeline_v1 回执；Source.details 增加 pipeline_backlog_v1 游标；原 checkpoint 不变。
最近20次流水线续跑回执有界保留，原数据库任务、Raw/Evidence 历史不删除。
Ctrl+C 持久化 CANCELLED 并保留已完成内容；原中断领域任务仍需显式恢复，不被擅自改成成功。

情报状态包括 DISCOVERED、NORMALIZED、ENRICHING、VERIFIED、AVAILABLE。
核验结论另列 CONFIRMED/PENDING/CONFLICT/INSUFFICIENT_EVIDENCE。AVAILABLE 仅表示可查，不是全局确认。
观测时间来自原存储，刷新页面不产生新观测。LIVE/MOCK/UNSPECIFIED 分开，历史 Mock 不被续跑改标 LIVE。

## 4. Agent 与资产复用

真实保存的数据通过原 Tool Gateway 的 get_vulnerability/get_evidence 成功读取；不直接请求模型或工具外部接口。
另外用明确合成来源，实际运行原 Investigation Agent 和专业 Verification Agent，证明新入库情报可进入原链路。
这项测试不是新的真实模型问答实验，也不是准确率验证。

只有显式配置 AEGIS_ASSET_OWNER 时，才对该用户已存在且组件匹配的库存调用原资产重算。
默认没有创建资产、猜测版本、扫描企业环境。核验、风险、Gate 仍由原规则执行。

## 5. API 和前端契约

新增两个只读接口：

```text
GET /api/v1/intelligence/records
GET /api/v1/intelligence/monitoring/runs
```

RecordPage 返回来源、生命周期、核验状态、模式、实际富化进度和原观测时间。
PipelineRunPage 返回源运行/周期ID、原采集状态、处理/失败/积压根任务、受控错误。
不返回凭据、数据库配置或资产身份，不触发模型、采集和重算。
原调查/PoC接口保持兼容；当前完整HTTP清单50项，情报相关8项。
实际 OpenAPI、TypeScript、客户端和前端交接镜像已同步。

## 6. 真实验证

在新建隔离数据库中进行两轮定时采集与一次收尾续跑，均为 LIVE，未读取 Benchmark/标准答案。
三轮共执行6个根富化任务和3个依赖输出，末轮积压根任务0。
实际保留1条漏洞、1篇博客、14个知识块及缓存真实 Embedding、7份原始记录、5条 Evidence 与5条原核验记录。
由于来源失败及部分富化结果，周期保持 PARTIAL，没有编成 SUCCESS。
两个新增GET及原来源GET均200；原 get_vulnerability/get_evidence 成功并返回证据引用。
详见 docs/phase14b2/live-receipt.json 和 live-tool-reuse.json。

## 7. 修改文件

- monitoring：新增 automation_schemas.py、framework.py、pipeline.py、scheduler.py、lifecycle.py、automation_cli.py；原 CLI 增加显式模式。
- api/intelligence.py：增加两个只读路由。
- frontend/contracts/monitoring.ts、intelligence.ts：类型和客户端；未修改队友页面。
- 实际 OpenAPI/TypeScript/接口清单及 AegisAI_FRONTEND_HANDOFF_PACKAGE 镜像；导出脚本和便携CI入口。
- test_phase14b2_pipeline.py、test_phase14b2_agent.py、原HTTP边界清单测试及本阶段文档。

708个已有 Agent、Planner、Runtime、Orchestrator、Gate、Model、原富化/资产/采集/标准化、数据库迁移及评测/实验文件保持原字节。

## 8. 测试和审查

本阶段新增46个流水线/边界用例及1个原 Agent复用用例，最终专项47项通过。
最终便携CI基线673项通过，1项已有缓存真实Embedding用例按原规则明确排除。
原前端23项、工程18项、TypeScript、JavaScript语法、实际契约一致性检查通过；前端本来没有构建脚本，不虚构build结果。
独立只读代码审查已通过；来源模式、积压饥饿、取消、依赖失败、时间和RSS身份等审查发现均有回归。

第一次全量回归1622项通过、2项已知 UnknownContext 失败、7项夹具错误。
七项来自复用测试库中的固定 pkg:pypi/vllm 唯一约束冲突；新的合成 Agent 测试已改用原夹具的唯一包名。
新的隔离库上，受影响版本工具及Agent复用复核9项通过。原运行和错误记录保留。
最终干净库完整回归结果另见 docs/phase14b2/test-summary.json；不是用工程测试数量表达安全准确率。

## 9. 限制与停止

这是本机显式启动的有界 worker，没有安装自动开机服务或分布式调度。
来源网络失败、窗口覆盖和旧工作恢复仍需运维处理；未进行大量抓取。
没有建立真实企业库存，也没有强行生成资产风险。
没有新 Agent、Gate放宽、Benchmark扩展、准确率实验或自动合并队友代码。
本阶段完成后停止；上游PR未合并时，本分支也不能被描述为 main 已发布。

操作说明：docs/phase14b2/OPERATIONS.md；前端说明：docs/phase14b2/FRONTEND_MONITORING_HANDOFF.md。
