# AegisAI 后端

当前已包含 Phase 11-D 的调查闭环和 Phase 12-B 的 8 个调查 HTTP 操作，迁移 head 为 0004。Planner、三专业 Agent、Integration Gate 和 AnswerEnvelope 的接口说明见 [调查 API](../docs/PHASE12B_INVESTIGATION_API.md)。Dify 不在运行链路中。

本后端在 8000 提供 API，现有七页骨架及同源代理在 8769；8768 是历史 Mock 原型。数据来自配置的数据库，不代表模型已经配置。默认 Mock 不提供 PlannerPlan，普通调查会返回 PLANNING_FAILED；受控离线闭环和真实模型调用须分别验收。先读 [本地联调与演示检查](../docs/BACKEND_DEMO_STABILITY.md) 和 [当前状态](../CURRENT_STATUS.md)。以下 Phase 6—8 同步、重放与资产说明保留为历史操作入口，测试数量不是当前验收结果。

## 当前机器启动

在项目根目录打开 PowerShell。已有 Python 环境与官方 PostgreSQL 便携缓存；脚本仅启动本项目自己的开发 cluster，不安装 Windows 服务。

```powershell
& './backend/.venv/Scripts/python.exe' backend/scripts/local_database.py start
$env:AEGIS_DATABASE_URL='postgresql+psycopg://aegis_local@127.0.0.1:55436/aegis_phase6'
$env:PYTHONPATH=(Join-Path (Get-Location) 'backend')
& './backend/.venv/Scripts/python.exe' -m alembic -c backend/alembic.ini upgrade head
& './backend/.venv/Scripts/python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果当前 API 已在运行，无需重复启动。[接口文档](http://127.0.0.1:8000/docs)与[真实漏洞列表](http://127.0.0.1:8000/api/v1/vulnerabilities)可直接打开。开发数据库仅监听 127.0.0.1:55436，使用本机 trust；这是本地开发配置。停止开发数据库：`python backend/scripts/local_database.py stop`。

## 真实同步与原文重放

另开同目录终端，沿用上述环境设置。

```powershell
& './backend/.venv/Scripts/python.exe' -m app.cli sync --source CVE_LIST --limit 1
& './backend/.venv/Scripts/python.exe' -m app.cli sync --source OSV --limit 10
& './backend/.venv/Scripts/python.exe' -m app.cli sync --source CISA_KEV --limit 100
& './backend/.venv/Scripts/python.exe' -m app.cli sync --all --limit 100
& './backend/.venv/Scripts/python.exe' -m app.cli sync --source CISA_KEV --limit 100 --recheck
& './backend/.venv/Scripts/python.exe' -m app.cli replay --raw-id REPLACE_WITH_REAL_RAW_UUID
```

`--limit` 限制本次处理，不保证一定有同等数量的新记录。CVE 扩大基线时扣除已覆盖路径；OSV 重读 overlap 会跳过旧记录；KEV 先保存并校验整个目录，再逐条处理。`partial` 表示还有 pending 或逐条失败，不能宣传为全量完成。重放只支持 CVE/OSV 单条原文，使用当前 normalizer 版本，完全不访问网络；KEV 目录通过 source sync 的条目上下文重放。CLI 对 failed 返回非零，对 partial 返回正常进程状态并明确输出 pending。

CVE 使用官方 Git 元数据与固定 commit 的官方 HTTPS JSON；不执行检出的文件。OSV 当前只覆盖 PyPI 有限基线及 modified_id.csv 前 1000 行；不完整发现窗口不推进全量 watermark。KEV 完整目录下载不等于完整域数据入库。各项限制见 [KNOWN_ISSUES](../reports/phase6/KNOWN_ISSUES.md)。

## 新环境与 Compose

使用 Python 3.12 创建虚拟环境并安装 `backend/requirements.txt`；实际锁定包、用途与许可见 [第三方说明](../reports/phase6/THIRD_PARTY_NOTICES.md)。复制 `.env.example` 的配置到安全环境；应用从环境变量读取，不会自动读取 .env 文件，示例 CHANGE_ME 必须替换。不得把真实密码提交到文件。

`docker-compose.dev.yml` 默认启动 PostgreSQL，backend 属于 api profile。本机没有 Docker，本阶段只做静态配置核验，未宣称镜像构建/启动成功。支持 Docker 的机器按以下顺序执行；先从安全环境设置 AEGIS_DB_PASSWORD：

```powershell
 docker compose -f docker-compose.dev.yml up -d postgres
 docker compose -f docker-compose.dev.yml run --rm backend python -m alembic -c alembic.ini upgrade head
 docker compose -f docker-compose.dev.yml --profile api up -d
 docker compose -f docker-compose.dev.yml exec backend python -m app.cli sync --all --limit 10
```

Compose 使用独立数据库及 Git 缓存 volume，发布到本机端口 5432/8000。端口被已有开发实例占用时，先调整映射或停止自己的实例。应用不在 API 启动时偷偷迁移。当前有本机Review写入的可配置Bearer保护与小批排程，没有完整IAM、TLS、常驻队列或生产恢复机制。

## 测试

真实开发库与专用空测试库严格分开；迁移往返会清空测试 schema，绝不能把测试 URL 指向真实数据。测试 fixture 逐项 rollback，测试后关闭专用 cluster。

```powershell
& './backend/.venv/Scripts/python.exe' backend/scripts/test_postgres.py start
$env:AEGIS_TEST_DATABASE_URL='postgresql+psycopg://aegis_test@127.0.0.1:55435/aegis_phase5_test'
$env:AEGIS_DATABASE_URL=$env:AEGIS_TEST_DATABASE_URL
& './backend/.venv/Scripts/python.exe' -m pytest backend/tests -q
& './backend/.venv/Scripts/python.exe' backend/scripts/test_postgres.py stop
```

运行器把迁移URL与测试URL同时设为专用aegis_phase5_test；只设置测试URL会导致迁移测试配置错误。最新结果见[TEST_RESULTS](../reports/phase8/TEST_RESULTS.md)。网络mock只用于可重复的适配器单测；真实同步证据单独保存，不把fixture计入采集数量，不生成虚假Benchmark。

## 模块职责

- app/core：配置、允许地址、统一 HTTP 重试/限速、结构化日志。
- app/collectors：Git/HTTP 采集、来源检查点、原文 envelope。
- app/normalizers 与 schemas：来源格式 → 中间契约；不负责数据库写入。
- app/services：产品、基础版本、AI 相关性 V0、身份解析、同步事务编排。
- app/repositories：持久化与只读查询；app/db 保留 Phase 5 模型。
- app/api 与 main.py：五条查询路径、会话生命周期和参数约束。
- resources：三源运行目录、人工维护的 AI 产品注册表、真实种子 ID。种子 ID 只决定请求顺序，数据仍重新从官方获取。

失败Source不使应用健康检查变红；数据库不可用才返回503。API中的verification_status=pending表示来源陈述尚未完成核验。旧source_variants保留来源断言状态；claims/verification_results显示逐结论核验/adopted。历史Phase7报告保持冻结；本轮完成Phase8主体工作后停止，不自行进入Phase9。


## Phase7调查、排程与复核

调查前切回开发库，不沿用测试URL。

```powershell
$env:AEGIS_DATABASE_URL='postgresql+psycopg://aegis_local@127.0.0.1:55436/aegis_phase6'
& './backend/.venv/Scripts/python.exe' backend/scripts/enrich.py investigate --target CVE-2026-64849
& './backend/.venv/Scripts/python.exe' backend/scripts/enrich.py investigate --target CVE-2026-57173 --kind epss
& './backend/.venv/Scripts/python.exe' backend/scripts/enrich.py schedule --target CVE-2026-64849 --limit 1
& './backend/.venv/Scripts/python.exe' backend/scripts/enrich.py due --limit 3
```

CLI每任务输出JSON，保留sources/status/时间/计数/errors/trace。FAILED需查看errors，NO_RESULT/PARTIAL有范围；CLI不以进程退出码代替每任务状态。各HTTP读30s、有限重试/记录上限，没有全任务看门狗。可从安全环境设置AEGIS_GITHUB_TOKEN；凭据不写入项目，未配置时遵守公共限流。

新增漏洞子路径enrichment/claims/evidence/pocs/patches/timeline，详情聚合含EPSS、KEV、版本、核验、冲突、复核和事件。GET reviews/{id}返回证据与审计；POST reviews/{id}/resolve默认503关闭。安全配置AEGIS_REVIEW_TOKEN及AEGIS_REVIEW_ACTOR后需Bearer，actor由服务器确定。正文含expected_revision、expected_claim_revision、request_key、status、value、reason、evidence_ids；重复键幂等，旧修订409，无合法支持422。人工替换已采用值有单独审计。

所有PoC仅静态检查，未运行利用代码。patched表达或官方包标识无法归一化时保留未知；28条样本尚待人工标注，不报告准确率。

## Phase8资产、SBOM与风险

最新迁移0003扩展资产环境/暴露面/组件规范版本及四张库存事件、风险快照、风险变化、重算任务表。当前292项工程测试通过，49表/25历史保护，零ORM偏差；前两份迁移及Phase1—7报告保持冻结。

资产API默认关闭。先在安全的本地环境设置AEGIS_ASSET_TOKEN和AEGIS_ASSET_OWNER，再启动API；Bearer token由客户端使用，owner由服务端确定，正文不允许自选身份。交付时运行服务使用仅存内存的临时token；需要自行访问资产库存时，用新本地凭据重启服务。不得将真实token写进项目或报告。

手工组件通过POST /api/v1/assets/{id}/components；SBOM通过POST /api/v1/assets/{id}/sbom，原JSON体和X-Request-Key，支持CycloneDX1.6/SPDX2.3，最大2MiB/1000组件。复用同资产导入可返回added/updated/removed；保留manual清单。版本升级PATCH需要expected_revision和request_key；GET risks、risk-changes、inventory-history、reviews均需owner鉴权。详细字段见[Tool V2](../docs/tooling/TOOL_CONTRACTS_V2.md)。

管理员CLI使用开发库环境。库存变化自动局部重算；情报变化需安排下面两项命令定期运行，当前没有常驻调度服务。dispatch仅检查相关依赖并排程，包含无Phase7事件的新来源范围，due有3次有限重试；不在GET中重算。

```powershell
$env:AEGIS_DATABASE_URL='postgresql+psycopg://aegis_local@127.0.0.1:55436/aegis_phase6'
& './backend/.venv/Scripts/python.exe' backend/scripts/assets.py dispatch --limit 10
& './backend/.venv/Scripts/python.exe' backend/scripts/assets.py due --limit 3
```

PyPI使用确定性PEP440比较；其他未验证生态、范围冲突、过期或未核验来源保留UNCERTAIN/UNKNOWN。产品相关补丁不自动表示包/分支适用。实际三例采用公开真实漏洞与明确演示库存，100组件受控性能见[Phase8实测](../reports/phase8/performance_final.json)。30条匹配评测仍待人类标注，正式阶段状态PARTIAL；交付后停止，未进入Phase9。
