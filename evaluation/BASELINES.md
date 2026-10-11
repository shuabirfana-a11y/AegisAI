# 四基线设计与实际可用范围

| 变体 | 真正执行路径 | 默认可用 | 禁止误称 |
|---|---|---|---|
| keyword_search | 冻结官方投影 → 词项检索 → 字段/引用展示，其他任务 UNKNOWN | 是 | 检索命中不证明安全判断正确；无版本推理、LLM、核验 |
| rag_only | 相同词项检索与 top-5 资料 → 现有 Model Gateway.generate_structured | 否，缺真实生成模型 | 不能以检索结果或 Mock 输出冒充 RAG 答案 |
| fixed_workflow | 原公告字段 → 现有 parse_expression/compare_version → 显式参考分诊政策 | 是 | 仅政策符合性与固定流程；没有专业核验 Agent，不能叫完整 AegisAI |
| aegisai | 真正 Python InvestigationOrchestrator → Planner/三 Agent/Gate/AnswerEnvelope/Trace | 否，缺真实模型、专用数据和请求映射 | 不用旧 HTTP assistant 冒充 Phase 11-D，不捏造新 API，不手工拼 Artifact 冒充执行 |

默认四变体都有逐例记录。两个已实跑变体各 49 条成功返回；另外两个各 49 条 NOT_EVALUATED。成功是取得结构化响应，不代表标准答案匹配；正式质量指标没有人审基准，所以为空。

## 真实模型的显式入口

保持现有 Model Gateway 配置变量：`MODEL_PROVIDER=openai_compatible`、MODEL_NAME、MODEL_API_BASE、MODEL_API_KEY，或显式允许的本地兼容服务。凭据只放本机环境。调用 `--live-model` 才启用真实生成，默认从不触发付费服务。Mock text provider 或 `result.is_mock=true` 一律排除。评测 RAG 不需要 embedding 下载；未使用的 Gateway embedding adapter 配为 Mock，该结果不计入任何模型分数。

```powershell
& backend/.venv/Scripts/python.exe evaluate.py --live-model --output evaluation/reports/my-live-run
```

此命令只启用 RAG；没有 native 配置时完整 AegisAI 仍 NOT_EVALUATED。真实模型名称、prompt 版本、每例 usage/request_id 和源码/资料哈希写入结果，endpoint、key、数据库密码不会写入。

## 真实 Phase 11-D 原生适配条件

额外传 `--live-aegisai-requests evaluation/experiments/<prepared-map>.json`，并设置 AEGIS_BENCH_DATABASE_URL、AEGIS_BENCH_ACTOR。数据库仅允许 loopback PostgreSQL，库名 `aegis_bench_test` 或 `aegis_phase5_test`；绝不连接开发/生产库。请求映射只能来自 evaluation/experiments 树，内容为 question ID → 真实 InvestigationRequest，不能包含答案/标注字段。目标、问题、组件、版本必须与测试输入相同；fresh request_key 每次实验生成，避免把 idempotent replay 当新执行。

数据需已用原有采集/规范化链路准备好。适配器不建库、不迁移、不造资产、不导入数据、不清空表。启动时只读验证 RawDocument 数量、ID、source_url、raw bytes 哈希与 parsed payload、原公告字段和冻结语料完全一致；不一致或缺少配置不执行。成功 opt-in 之后 Orchestrator 只执行其原本的 Trace/Artifact 审计写入。正向调用适配测试使用明确 fixture；本阶段未跑真实模型/数据库 Orchestrator，因此不声称实测通过。

当前 Native AnswerEnvelope 最多一个资产，不能覆盖所有本批多资产问题；缺少准备请求或超范围返回 NOT_EVALUATED。Native priority 保留 P0/P1/P2/P3/DEFER/REVIEW_REQUIRED，不人为改成参考策略的 MONITOR/REVIEW。CWE/summary/CVSS vector 等不能在 AnswerEnvelope 确认的字段不编造；保留 native 引用，后续人工按源映射审核。版本、政策、输出字段需在正式人审数据中统一后，方可声称比较了真实 AegisAI 与普通 RAG。

## 公平性要求

同一冻结语料、时间截点、资产输入、ground truth 与失败预算；生成基线需同 provider/model。当前固定/关键词无需模型，不能把速度直接与在线模型比较。完整 AegisAI 的模型 prompt 使用现有 Planner 版本，不重写为此评测的提示词。当前参考政策和原生业务风险政策不同、跨资产范围未齐，因此整体报告保持 NOT_COMPARABLE。

后续应增加隔离的核验消融实验（同模型、同资料、开/关核验），而非把本批 reference match 差当作核验改进。本阶段不修改核验核心，也不新增该开关。
