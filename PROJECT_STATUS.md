# AegisAI 当前项目状态报告

> Phase 0 接管审计，2026-10-08。本文只评估现状并规划迁移；没有以本报告为由修改产品代码、迁移数据库、安装依赖或启动新 Agent。百分比是对目标架构的工程成熟度估计，不是比赛分数、准确率或正式验收结果。

## 1. 项目概况

**项目名称：** AegisAI —— 面向 AI 生态的可信安全情报与自主调查智能体系统。

**当前结论：** 这是已经有真实数据、后端、证据链、工具层和前端页面的项目。应在现有模块上补齐模型接入、可靠性、评测和交付，不应重新搭建。原有报告把 Tool Gateway、混合检索、确定性 Agent 和前端骨架列入“历史 Phase 9”，总体标记 PARTIAL；本报告沿用用户新提出的 Phase 9—12 **迁移批次**，两套编号不能被误读为这些能力尚未开发。

| 项目 | 审计结果 |
|---|---|
| Backend | Python 3.12、FastAPI、Pydantic、SQLAlchemy；OpenAPI 展开后有 33 个路径、34 个 HTTP 操作。[入口](backend/app/main.py)、[API](backend/app/api/) |
| Frontend | 原生 HTML/CSS/浏览器 ES Modules，Node 内置 HTTP 服务；没有 React、Vue、Next.js 或 TypeScript。[前端](frontend/) |
| Database | PostgreSQL 17 开发库、Alembic 0001—0004；50 张业务表分布于 raw/core/intel/app/evaluation，另有 public.alembic_version。没有 MySQL、SQLite、Redis 或 pgvector 扩展。[模型](backend/app/db/models/)、[迁移](backend/alembic/versions/) |
| Deployment | 本机启动脚本、后端 Dockerfile、只包含 PostgreSQL 与后端的开发 Compose；没有已验证的公网网站、HTTPS、完整生产发布/备份恢复流程。[开发 Compose](docker-compose.dev.yml)、[本机脚本](scripts/) |

主要目录：requirements 为赛题、需求与评分追踪；research 为数据源研究；design 为冻结的产品/数据/架构设计；backend 为 API、采集、富化、资产、知识检索和 Agent；frontend 为真实 API 页面；prototype 是独立 Mock 原型；integrations/dify 是可选的历史 Dify 桥接资产；evaluation 和 tests 分别存候选评测与工程测试素材；docs/tooling 为工具契约；reports 为各阶段历史证据；work 为开发缓存、数据库与过程记录；scripts 为本机启动/停止脚本。

审计依据是当前源码、迁移、只读数据库查询及已有运行记录。2026-10-08 本次只读查询曾读到开发库和 API；随后检查时 8000/8769/55436 均已关闭，不能据一次成功查询宣称服务可常驻。历史全量测试报告为 2026-10-06 的 378 个后端通过项；此后代码有变动，本次 Phase 0 没有重新运行全量测试。[历史测试记录](reports/phase9/TEST_RESULTS.md)

## 2. 已完成模块

### API 与数据库

| 接口组 | 代表路径 | 功能与当前状态 |
|---|---|---|
| 基础查询 | /health、/api/v1/sources、/api/v1/sync-runs | 健康、来源与同步任务；代码已存在，健康检查对数据库失败返回 503。[routes.py](backend/app/api/routes.py) |
| 漏洞 | /api/v1/vulnerabilities、/{id} 及 enrichment/claims/evidence/pocs/patches/timeline 子路径 | 列表、详情、富化与证据分页；代码已存在。[routes.py](backend/app/api/routes.py)、[enrichment.py](backend/app/api/enrichment.py) |
| 复核 | /api/v1/reviews、/{id}、/{id}/resolve | 列表、详情和受令牌保护的人工决议；写入默认关闭，需服务端配置。[enrichment.py](backend/app/api/enrichment.py) |
| 资产 | /api/v1/assets、/overview、/{id}/risks、组件、SBOM、风险变化和复核 | 基于 owner 的私有库存、风险和变更；代码已存在，Bearer 由服务端校验。[assets.py](backend/app/api/assets.py) |
| 工具与问答 | /api/v1/tools/contracts、/{name}、/api/v1/assistant/query、/runs/{id}/tasks、/trace | 30 个登记工具、异步问答和可审计轨迹；代码已存在。[tools.py](backend/app/api/tools.py)、[assistant.py](backend/app/api/assistant.py) |

2026-10-08 的只读数据库快照：8 个来源、369 份 RawDocument、1415 条 SourceObservation、278 条漏洞、529 条影响版本范围、48 条 Claim、76 条 Evidence、7 条 Conflict、68 条 VerificationResult、54 条 ReviewTask、5 个演示资产、20 篇 KnowledgeDocument、98 个 Chunk/Embedding、30 条 AgentRun。数据是**本地有限范围**，不是全球 CVE 全量，也不是经过人工标注的比赛准确率。

### 情报链与可信核验

- 主采集器已接入 CVE Program/cvelistV5、OSV（其中可取得 GHSA 记录）和 CISA KEV，保存原文、来源观察、同步记录与增量状态。[采集器](backend/app/collectors/)、[来源配置](backend/app/resources/sources.json)
- 富化代码包含 CVSS 2/3/4 与 CWE 归一、产品和版本识别、PyPI 版本比较、EPSS、定向厂商公告、GitHub PoC/补丁候选、KEV 及资产风险。[归一化](backend/app/normalizers/)、[富化](backend/app/enrichment/)、[资产匹配](backend/app/assets/)
- Claim、Evidence、来源原文定位、当前证据与来源关系、冲突检测、可信门禁及人工复核均有独立实体和服务。PoC 只做静态关联，不能当作利用可执行性证明；补丁候选也不等于该资产已有可用修复。[核验](backend/app/enrichment/verification.py)、[冲突](backend/app/enrichment/conflict.py)、[门禁](backend/app/assistant/gate.py)
- Tool Gateway 已有强类型参数、权限和调用预算；Query Router、Task Contract、DAG 调度、重试/有限重规划、Investigation/Verification/SecurityAnalysis 三个角色、Handoff 与 Integration Gate 已存在。角色是**确定性代码**，尚非模型驱动的自主推理。[工具](backend/app/tooling/)、[编排](backend/app/assistant/)

### 前端与评测准备

前端已有情报总览、漏洞中心、漏洞详情、资产风险、证据复核、智能问答、系统状态这 7 个路由；通过同源代理直接调用 FastAPI。另有 8768 的 Mock 原型，不应将它计为真实联调。[路由](frontend/public/modules/router.js)、[页面](frontend/public/modules/pages/)、[服务](frontend/server.mjs)

AegisBench-v0.1 已准备 24 道候选题和计算框架，但人工复核的 Ground Truth 为 **0 条**。因此不能报告 Precision、Recall、F1、问答准确率或 Agent 消融收益。[评测说明](evaluation/README.md)、[清单](evaluation/datasets/AegisBench-v0.1/manifest.json)

## 3. 部分完成模块

| 模块 | 已有部分 | 尚待完成或证据不足 |
|---|---|---|
| 数据覆盖 | 三个主采集器、EPSS/GitHub/定向 Vendor 富化；2026-10-08 只读来源状态中 CVE_LIST、EPSS、GITHUB、VENDOR_PYTORCH 为 succeeded | OSV、CISA_KEV 为 partial，VENDOR_MLFLOW/VENDOR_VLLM 为 failed；直接 NVD、独立 GHSA、RSS/博客及通用爬虫未接入。不能把“8 个 Source 行”等同于 8 类稳定监测源 |
| 版本与富化 | CVSS/CWE、PyPI 版本解析、PoC/Patch 静态候选及资产匹配 | 非 PyPI 生态比较受限；来源范围冲突与未核验断言存在；PoC 可用性、补丁适用性及召回率没有充分人工真值。[Phase8 限制](reports/phase8/KNOWN_ISSUES.md) |
| Hybrid Retrieval | SQL、关系查询、本地 384 维语义向量可组合；20 篇文档、98 个向量 | 向量是 PostgreSQL Float 数组，最多有界读取 1000 片段后在应用层精确余弦排序；没有 pgvector/ANN，也没有大规模性能结论。[检索](backend/app/knowledge/retrieval.py) |
| Agent | 规则路由、有界计划、并行 DAG、工具和证据门禁可运行 | 无生成模型网关、模型辅助规划/多轮对话；进程内执行池、服务重启后运行恢复和长期任务状态还需验证。[运行服务](backend/app/assistant/service.py) |
| Frontend | 七个真实 API 路由，问答轮询与任务轨迹；本机演示代理可保管后端令牌 | 目前仍是功能骨架，部分字段直接展示原始 API 结构；资产页的演示 owner 现场返回 0 项，而库内 5 个资产属于两个其他 owner；未做公网访问与评委完整流程验收 |
| 自动化/部署 | 有开发 Compose、Dockerfile、本机脚本与部分重试排程 | Compose 不含前端和公网入口；当前 Docker Linux 引擎不可达，本机服务也未保持常驻；没有可提交给评委的公网 HTTPS 链接、生产监控/备份恢复验证 |

**数据源选型归类：** 已接入主采集的是 CVE_LIST、OSV（间接覆盖部分 GHSA）和 CISA_KEV；EPSS、GitHub 与定向 Vendor 是按需富化源。已规划但未实现独立采集的有 NVD、GHSA 直连、RSS/安全博客；通用网页爬虫当前缺失。是否扩源应以评分要求、来源许可和可验证性为依据。[数据源选型](research/data_sources/FINAL_DATA_SOURCE_SELECTION.md)

## 4. 未完成模块

- **Model Gateway：** 当前没有统一的生成模型接口、模型路由、凭据管理、调用/Token 计量、降级与模型响应校验；用户已明确停用 Dify，不能把本地 Embedding 当作生成模型。
- **正式质量评测：** 无人工批准的 gold，无独立时间切分；RAG-only 与“无核验”消融所需可比运行适配器未就绪。
- **生产交付：** 前端未纳入完整部署栈；公网域名/HTTPS、凭据与身份方案、常驻任务恢复、稳定性和故障恢复证明未完成。
- **数据源扩展：** NVD 直连、GHSA 直连、RSS/博客通用监测等尚未实现；是否新增须先按赛题评分与权威性确定优先级，不能为了凑源数牺牲可信度。

### Dify 相关现状与迁移影响

文件位于 [integrations/dify](integrations/dify/)：两份 Workflow DSL、Compose 覆盖、网关、导入/验证脚本和角色 Prompt。它们是历史可选桥接资产。当前 [后端运行代码](backend/app/)与[前端运行代码](frontend/public/)没有 Dify API/SDK/工作流导入；真实 Dify 应用、知识库、模型提供商及 Dify→Backend 调用均无成功验收。过去的离线 DSL 校验不能算真实运行。[历史 Dify 记录](reports/phase9/DIFY_INTEGRATION.md)

**迁移建议：** 按用户最新决定，运行链保持“前端 → FastAPI → 自有 Agent Runtime → Tool Gateway/检索/核验 → PostgreSQL”。保留 integrations/dify 作为历史资料，不把它放进启动、验收或部署的必需路径；不搬移/复制已经在后端实现的富化与核验逻辑。模型需要时接入独立 Model Gateway。

## 5. 与最终架构差距

| 目标层 | 对应现有实现 | 差距判断 |
|---|---|---|
| 用户交互层 | 七个原生 JS 页面、同源 API 代理 | 功能入口齐，产品呈现和端到端评委体验不足 |
| FastAPI 服务层 | 34 个 HTTP 操作、Pydantic 契约、部分鉴权 | 生产身份、限流、部署与恢复未闭环 |
| Query Router / Task Planner | [router.py](backend/app/assistant/router.py)、[orchestrator.py](backend/app/assistant/orchestrator.py) | 已有规则路由与确定性计划，缺模型辅助理解与经过验收的自由规划 |
| DAG Scheduler / Tool Gateway / Integration Gate | [graph.py](backend/app/assistant/graph.py)、[gateway.py](backend/app/tooling/gateway.py)、[gate.py](backend/app/assistant/gate.py) | 核心已有，重点应是重启恢复、边界与真实对照实验 |
| 专业 Agent | 三个确定性角色 | 名称和执行契约存在，但不是三个独立 LLM Agent |
| 安全情报引擎 | 采集、富化、Claim/Evidence/Conflict/Review 与资产匹配 | 来源覆盖和人工核验质量未达到可宣称完整/准确的程度 |
| Hybrid Retrieval | SQL + 关系 + 本地向量 + 工具 | 路径存在；pgvector 缺失，数据规模和检索效果未正式评测 |
| PostgreSQL + pgvector | PostgreSQL 17、0004 知识向量表 | pgvector 扩展及索引未安装/迁移；当前使用 Float 数组 |

**工程成熟度估计：整体约 55%。** 分项估计：数据基础 75%、后端服务 80%、情报能力 60%、Agent 能力 55%、前端能力 50%、部署能力 20%。这些数字只表示目标能力存在性和验证深度的审计判断，不能替代比赛评分或实测质量指标；整体值按关键短板与各项平均取整。

## 6. 最大风险

1. **可信度无法量化。** 24 道候选题没有人工批准的 gold，现有数据源还存在 partial/failed；准确率、召回率、F1 与 Agent 优势都无法诚实宣称。
2. **“Agent”概念可能被高估。** 现有多角色是确定性工具编排，尚无 Model Gateway 或真实模型规划；答辩时应明确区分已经实现的可审计自动调查与尚未实现的模型驱动能力。
3. **演示链未闭合。** 当前本机代理默认 owner 与现有三个 Phase8 演示资产 owner 不同，资产概况显示 0；浏览器快照中本机演示模式的令牌表单仍可见；服务后来退出；评委可访问的公网地址也未形成。不要直接把本机演示模式暴露到公网。
4. **覆盖与版本适用性边界。** CVE/OSV/KEV 的本地有限范围、Vendor 失败和只可靠比较 PyPI，会使“未找到”不能解释为“安全”；PoC/Patch 仍需人工/来源范围核验。
5. **运行和交付风险。** Docker 引擎当前未运行，开发 Compose 没有前端/HTTPS；没有常驻队列恢复、备份还原与完整 DevOps 证据。本目录目前不是 Git 仓库，缺少常规变更追溯；历史 378 项测试在最近代码变动后未做全量复跑。

## 7. 下一阶段开发建议

先冻结“已有能力清单”：Tool Gateway、SQL/关系/向量检索、Claim/Evidence/Conflict、DAG 和门禁均复用。新架构的最小新增点是独立 Model Gateway、模型输出到既有 Task Contract 的受控适配及运行恢复。先让一条真实问题从现有 FastAPI 走完整证据链，再决定是否加入 pgvector；98 个向量还不足以证明必须立即迁移 ANN。

模型服务由用户后续选择，接口先定义可插拔适配和失败时的确定性退路，不引入 Dify。所有生成内容必须经过现有 Tool Gateway 与 Integration Gate，不能由模型直接写“已确认”事实。与此同时为 AegisBench 安排人工标注和独立样本，评测准备应与开发并行，但正式指标只能在 gold 审核完成后产生。

## 8. 推荐开发顺序

以下 Phase 9—12 是**新的迁移工作包**，不是重做历史阶段；“预计修改文件”表示将来实施范围，本次 Phase 0 未修改它们。

| 阶段 | 目标 | 输入 → 输出 | 预计修改文件 | 验收标准 |
|---|---|---|---|---|
| Phase 9：Model Gateway 与现有工具/检索整合 | 新增统一模型接口；复核已有 30 工具与 SQL/关系/向量边界，避免重复实现 | 输入：现有 Tool Contract V3、问答请求、模型服务选择与本地 Embedding；输出：受控模型调用契约、错误/预算/引用信息，保留确定性退路 | 新增建议：backend/app/model_gateway/；按需调整 backend/app/assistant/router.py、backend/app/tooling/gateway.py、backend/app/knowledge/retrieval.py 及对应测试；不重建 Tool Gateway | 真实模型可用时验证至少一条端到端调用；超时、无凭据、非法响应均安全降级；模型不能绕过工具权限或核验门禁；现有确定性问答回归通过 |
| Phase 10：Agent Runtime | 让现有 Router/Planner/DAG 接受受控模型建议，并解决运行恢复 | 输入：Phase 9 契约、现有 Task Contract、真实后端数据；输出：可追溯计划与任务状态、重启恢复/失败回收 | backend/app/assistant/{service.py,router.py,orchestrator.py,graph.py,storage.py}，必要时新增迁移和专项测试 | Fast/Deep 真实案例完整运行；重启后 pending/running 不丢失或被明确标失败；预算、超时、幂等及非法工具请求受控 |
| Phase 11：多 Agent 协作与 Integration Gate | 在现有三个角色上验证实际任务分工、交接和证据门禁价值 | 输入：Phase 10 Runtime、Claim/Evidence/Review、人工标注样本；输出：调查→核验→风险分析的可审计交接及对照实验 | backend/app/assistant/{roles.py,handoff.py,gate.py,contracts.py}、evaluation/ 的 runner 与经人工审核的 gold；保留旧门禁 | 冲突进入人工复核，缺证据弃答，伪造/过期引用拒绝；单角色与多角色在相同人工 gold 上可重复比较，不编造提升 |
| Phase 12：前端联调与可提交演示 | 把七个现有页面接成稳定评委流程并准备公开部署 | 输入：稳定 API、权限方案、真实演示资产与已验证案例；输出：可访问网站、演示路径和部署/恢复说明 | frontend/public/modules/pages/、frontend/public/modules/services.js、frontend/server.mjs、frontend/public/styles.css、frontend/tests/，另补生产部署配置 | 真实浏览器完成“总览→漏洞详情→证据→资产风险→问答→复核”；移动端/失败/空态可用；公网 HTTPS 与访问控制实际验收，后台令牌不暴露到浏览器 |

**顺序前提：** 在 Phase 9 实施前确认本报告与目标；在 Phase 11 统计任何准确率前完成人工 gold；Phase 12 公网发布前先解决本机演示 owner、身份与服务常驻问题。全程沿用现有数据库、API 和报告证据，不因新编号而重新开发已实现的模块。
