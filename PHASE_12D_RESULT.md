# Phase 12-D：本地真实模型Provider与前端接入准备结果

2026-10-12，AegisAI / ICT命题九。分支 `feature/phase12d-model-provider`，基于PR #8的Phase12C提交 `8198bd8d641604b8ee05f1478952416d3152fb53`。main未改动。

**交付状态：PARTIAL。Provider、配置隔离、公共Trace与前端契约、工程检查已经交付；真实模型规划可靠性和完整HTTP调查尚未验收，不能标记本阶段全部完成或比赛演示就绪。**

## 1. Provider架构与完成内容

复用 `Agent/Planner → Model Gateway → OpenAICompatibleProvider → 本机Ollama`。已安装Windows原生运行时与免费Qwen模型，不需要Linux、WSL、Docker或收费API。Mock仍用于测试；真实模型失败时不会自动切换云或Mock。未新增模型SDK、Agent框架、数据库迁移或HTTP操作。

实现安装/启动与限时探测脚本；新增可选Provider `reasoning_effort` 控制，默认不发送。调用日志沿用原Gateway，保留请求ID、Provider、模型、耗时、Token（未知为null）和安全错误码。

## 2. 配置与模式

两个独立JSON配置在 `demo/phase12d/`，模型服务只监听本机11434，安装/模型放在LOCALAPPDATA，源码和Git不包含模型文件。启动包装脚本临时设置子进程环境，完成/失败后恢复，不写永久环境；启动失败只清理本次已启动进程。数据库仍使用已有启动条件，不把模型安装器说成整套系统安装器。

文本配置REAL时Embedding仍为Mock，旧Embedding调用点未迁移。默认Mock没有PlannerPlan成功fixture，保留这个事实。[启动与配置](demo/phase12d/README.md)。

## 3. 已授权Schema补齐

真实联调发现模型Schema允许 `input_data.target`，实际Runtime只接受steps/required_fields。取得用户明确许可后，仅在 `backend/app/planner/schemas.py` 描述原TaskInput和原TaskContract的结构条件；保留Python字段、默认值、全部验证器和执行逻辑。完整互斥分支兼容服务端Schema解码，公共properties也保留。

提示词、任务白名单、Planner验证器、DAG、Scheduler、Runtime、专业Agent、Risk/Gate未修改。旧源码哈希基线文件原样保留，另用 [版本化例外](docs/phase12d/source_hash_exceptions.json) 固定三个已授权业务文件和两处测试时钟修正的前后摘要；其余原保护文件继续校验。

## 4. 真实模型结果

最终默认Qwen2.5配置：健康与文本通过；小型JSON5/5；两种Planner输入0/2验证通过，每种均原有最多2次尝试后FALSE_MISSING_INPUT。11条Gateway协议调用成功不表示合法计划。[完整实测记录](docs/MODEL_PROVIDER_TEST.md)。

Qwen3.5兼容配置曾有一轮Planner1/2合法，但复杂规划与后续配置不稳定。保留失败回执，不以孤立成功冒充稳定模式，不生成安全准确率。

## 5. HTTP与前端影响

最终实际本机TCP调查经原API进入Orchestrator并真实调用本地模型：Planner失败；0 Agent、0 Artifact、无IntegrationResult；AnswerEnvelope=FAILED。Integration接口409属正确的结果未就绪语义。持久化模型身份REAL可读取；重复失败答案一致、额外模型调用0。[HTTP摘要](docs/phase12d/http-check.json)。

TraceResponse只增加可选 `model_execution`：MOCK/REAL、provider、model、source=PERSISTED_PLANNER_CALL、attempt_count。尚无保存调用时为null；以存储回执判定历史身份，不用当前环境重标历史，也不把REAL当成功。兼容模型别名、超时/坏响应重试及不同确定模型名的拒绝已有测试。

OpenAPI、d.ts、团队交接包与清单同步，42个HTTP操作不变。创建响应旧model_provider/is_mock仍有原语义，复用调查时应读Trace的新字段。没有修改队友页面或前端Client。

## 6. 实际测试结果

历史1261等数量不作为本轮通过数，也不把重叠测试相加。

| 本轮实际命令/范围 | 结果 |
|---|---|
| 初始完整 `python -m pytest tests -q -k 'not test_cached_real_local_embedding_through_gateway'` | 1305通过、34失败；保存失败日志，不能称全绿 |
| 新专用测试库先跑 `pytest tests/test_migration.py -q` | 1通过，真实PostgreSQL迁移往返 |
| 新库的根目录test_*.py，排除已执行migration | 378通过；原有数据残留引发的计数失败消失 |
| 新库7个模块目录批量回归 | 963通过、2失败、1明确排除；该进程在修复前收集了哈希/并发测试版本，仍如实记失败 |
| 修复后 `pytest tests/orchestration/test_legacy_compat.py::test_old_api_and_business_source_hashes_are_unchanged tests/runtime/test_scheduler.py -q` | 9通过，批量两处失败已复测 |
| 最终 `python scripts/ci/run_backend_tests.py` | 466通过，1条真实缓存Embedding明确排除 |
| `pytest tests/investigation_api/test_model_execution.py tests/runtime/test_scheduler.py -q` | 22通过（含14条持久化身份测试） |
| `python -m unittest discover -s tests/engineering -q` | 18通过 |
| `npm --prefix frontend test` | 23通过 |
| 导出/契约/TypeScript检查 | 10份导出一致，42操作/5组Schema/40个合成对象；tsc退出0 |
| `node scripts/ci/check_frontend.mjs` | 17文件语法通过；应用build未配置 |

实际命令和摘要另存 [verification.json](docs/phase12d/verification.json)。工程合成数据不能作为真实模型效果；实际模型失败不能被受控成功场景覆盖。现有Starlette废弃警告与负向测试Pydantic枚举序列化警告保留。

## 7. 审查、安全与修改文件

独立审查确认已修复模型别名重试读取失败、探测中断残留旧ready/工作进程、前端启动异常遗漏清理后端。测试先复现故障再验证修复。正式数据、人工Ground Truth未修改，候选题未重写，zip收到49条DRAFT不计为APPROVED。

主要文件：`scripts/setup-local-model.ps1`、`scripts/start-model-demo.ps1`、既有启动器小范围修复；`demo/phase12d/`；`backend/scripts/probe_model_provider.py`及HTTP探测器；`backend/app/investigation_api/model_execution.py`、schemas/service；ModelConfig/Compatible Adapter两个可选配置改动；已授权Planner Schema；相关测试/CI列表；本报告、实测记录、CURRENT_STATUS、交接文档与类型导出、清单/ZIP。没有迁移目录或删除历史代码。

公开回执不含Key、数据库密码、应用访问令牌、私有部署配置、原始提示词/失败候选或模型大文件；源码配置示例只提供公开的loopback地址。本地私有诊断保留在忽略目录。仓库检查、密钥扫描和包完整性检查以verification记录为准。

## 8. 当前未满足项与风险

- 当前真实模型计划持续非法，完整真实调查链未通过，不能用于稳定比赛Live演示。
- 冷加载可能超过Gateway网络限时，需要先预热；不增加应用超时或放宽规则掩盖失败。
- 取消仍是已有协作语义，受理不等于立即中断同步模型请求。
- 真实Embedding、LLM答案表达、正式Ground Truth评测、公网网站均未在本阶段实现。
- PR #8尚未合并；本分支包含它的基础提交，发布/合并需明确依赖，不自动改main。

## 9. 下一步与停止范围

本轮工程交付到此，保留未通过验收状态。后续先针对真实模型与Planner兼容性作单独授权和小样本验证，再重新执行HTTP调查；不扩展Agent、不修改核验/Risk/Gate、不启动正式Benchmark或部署。不得把本报告理解为进入后续阶段的授权。
