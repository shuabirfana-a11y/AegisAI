> 此包不包含后端源码；文中命令须在完整项目中执行。本文件交付当前联调结果，不宣称真实模型演示就绪。

# Phase 12-C：前后端真实调查链路联调与 Mock 替换准备

日期：2026-10-11。项目：AegisAI / ICT命题九。稳定基线：main `8e0bfe6bd398d26fc7270e5f0b5aeb6d03d354fd`（PR #6、#7均已按负责人授权合并）。工作分支：`feature/phase12c-http-integration`。

## 1. 完成内容与实际结论

完成了本阶段的联调准备：八个调查HTTP操作、实际TCP执行链、公共Schema、现有TypeScript Client、冻结Answer读取、失败与取消语义、模型模式隔离、固定场景和当前交接包。

**专用测试库中，显式合成规划回执 + 实际业务服务的完整闭环通过；本机真实来源 + 默认Mock仍在规划阶段失败。** 本轮没有替换模型，也没有宣称比赛真实模型演示已就绪。

- 没有修改 `backend/app/`、Planner、Runtime、三个Agent、Tool/Model Gateway、Gate或前端页面。
- 没有新增API、数据库迁移、依赖、另一个Agent框架或预生成成功Artifact。
- 没有填写Ground Truth，49题SHA-256保持 `f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1`，人工登记仍0/49。
- 没有真实模型效果评测、正式AegisBench实验或公网部署。

## 2. 实际链路验证

### 受控完整链：SYNTHETIC_TEST

只用专用 `aegis_phase5_test` 数据库，复用原有 scenario(mode='complete')，固定vLLM0.6.0语义条件。唯一CVE/UUID绑定用于隔离测试；来源和规划回执均明确标为合成，不作为安全事实或标准答案。

临时Uvicorn本机TCP端口真实收到HTTP请求，执行现有 Orchestrator → Model Gateway结构化规划回执 → Planner验证 → Investigation Agent → Verification Agent → Security Analysis Agent → Integration Gate → AnswerEnvelope。

实际摘要：Planner=VALIDATED；3个专业Agent Run；5次实际Tool调用记录；3份实际生成Artifact；Gate=PASS；Answer=COMPLETE；3条引用。不是mock整个Orchestrator的返回值。八操作HTTP均为预期成功状态，公共响应逐一由当前Pydantic模型验证。

现有 `frontend/contracts/investigations.ts` 未修改，Node加载后通过同一TCP端口调用八操作，成功读取AnswerEnvelope。重复Answer读取与同键重复提交没有增加模型调用。

此外验证：默认Mock规划失败、REAL期望拒绝Mock身份、未授权401、不存在404、运行中Answer409、轮询超时不自动取消、协作取消最终CANCELLED且后续专业Agent没有运行。

原有 TestClient 两条回归也通过。TestClient是在进程内调用ASGI，不能当作TCP证据；本轮新增的独立端口测试补足了传输层验证。[FastAPI TestClient说明](https://fastapi.tiangolo.com/reference/testclient/)，[Uvicorn预绑定socket实现](https://github.com/kludex/uvicorn/blob/main/uvicorn/server.py)。

### 固定真实来源：REAL_SOURCE + 默认Mock

通过现有8769同源代理 → 8000后端，提交固定 CVE-2025-32434 / torch / PyPI / 2.5.1 查询。漏洞记录来自已采集本地数据；2.5.1是待判断条件，没有预填影响答案或库存资产。

实际创建202，status/trace/artifacts/answer/history/cancel可读取。Trace包含真实Planner审计，validation_status=PLANNING_FAILED，三个Agent未运行，Artifact均为空，Gate未产生，Integration GET返回409 RESULT_UNAVAILABLE；Answer GET返回200但answer_status=FAILED。

创建响应实际 model_provider=mock、is_mock=true。检查请求期望REAL，工具报告MODEL_MODE_MISMATCH，同时保留chain_error_code=PLANNING_FAILED。退出码1是正确的未就绪结果，不算成功闭环。没有在失败后回退为合成答案。

脱敏记录见 [HTTP摘要](../api/reference/phase12c-http-probes.json)。它只包含ID、状态、时间和计数，没有令牌、模型Key、原始Prompt、数据库密码或成功情报答案。

## 3. 八个API验证

| 操作 | 受控完整链 | 当前真实来源/Mock失败链 |
|---|---:|---:|
| POST /api/investigations | 202，实际Orchestrator | 202，实际Orchestrator |
| GET /api/investigations/{id}/status | 200，SUCCEEDED | 200，FAILED |
| GET /api/investigations/{id}/trace | 200，Planner与三Agent | 200，仅实际Planner失败 |
| GET /api/investigations/{id}/artifacts | 200，三Artifact | 200，三项null |
| GET /api/investigations/{id}/integration | 200，PASS | 409，RESULT_UNAVAILABLE |
| GET /api/investigations/{id}/answer | 200，COMPLETE，冻结结果 | 200，FAILED，冻结失败结果 |
| POST /api/investigations/{id}/cancel | 200，终态不逆转 | 200，终态不逆转 |
| GET /api/investigations/history | 200，主体范围内 | 200，主体范围内 |

不是每个200都代表成功；失败答案也有可消费公共Schema。运行中取消另测：cancel_requested=true后等待CANCELLED，不能把受理当成立即终止。

## 4. 前端联调与交接状态

- 已将 `docs/FRONTEND_HANDOFF.md` 从历史审查改为当前接入规范：41条路径、42操作、代理可接35个、7个旧写操作受限。
- 保留旧34操作LEGACY_DESCRIPTION_ONLY与新8操作STRICT_PYDANTIC区别，不声称旧响应已全部严格验证。
- 同步队友包的总交接、快速开始、API状态/清单/缺口、公共契约说明与调查页需求状态；删除了当前说明中“完整调查未开放”的过期判断。
- 保留原有历史Mock资料和验证记录，新增当前联调说明与验证摘要，更新MANIFEST和ZIP。
- 当前七个已有页面不变；现有/assistant仍走旧确定性问答。**队友智能调查工作台的UI接线仍由前端团队完成，本轮没有声称工作台已经开发完。**

前端现在可直接接入八个新调查API。使用当前公共TypeScript类型/Client；每1–2秒轮询真实状态，revision变化刷新Trace/Artifact，终态再读Answer/Gate。CORS、身份、幂等、取消、恢复待处理与未知值规则见 [当前交接](FRONTEND_TEAM_HANDOFF.md)。

## 5. Mock / Real与模型配置

新增固定场景与不含Key的配置样例见 [场景说明](../examples/phase12c-scenarios.md)：MOCK、REMOTE_COMPATIBLE、LOCAL_COMPATIBLE三组ModelConfig已离线验证。

远程/国产模型仅在实现现有兼容协议时可用该Adapter；必须配置实际模型名、HTTPS地址及服务器端Key。本地模型需要实际运行兼容服务；样例模型名和端口不代表已经安装模型。配置全部沿用现有环境变量，JSON样例不会自动加载。

配置样例的独立Embedding保持Mock，不迁移现有检索调用点；不能称作整个模型/检索链已经真实化。此轮没有请求任何真实模型服务、没有质量评估，也没有写模型对比实验。

检查工具只允许显式本机HTTP，拒绝用户名/密码URL、外部地址、路径/查询参数混用和重定向。每请求限时5秒，有限轮询；失败会覆盖旧检查摘要为失败，避免误读上次成功。输出仅为白名单审计元数据。

## 6. 修改文件

- 新增：`backend/scripts/probe_investigation_http.py`；模式/Schema/CLI测试 `test_http_probe.py`；TCP链路测试 `test_tcp_chain.py`；调用现有Client的 `client_probe.mjs`。
- 新增：`demo/phase12c/` 固定真实来源输入、受控场景定义、模型配置样例及说明。
- 修改：`backend/.env.example` 仅补配置说明；`scripts/ci/run_backend_tests.py` 将新无数据库检查加入已有CI基线。
- 新增/更新：本报告、实施计划、CURRENT_STATUS、当前前端交接文档/缺口、`docs/phase12c/` 验证摘要；队友交接包相关文档、清单与ZIP。
- 没有修改：业务源码、数据库模型/迁移、前端页面、生成的OpenAPI/类型/Client、候选题与人工标准答案。

## 7. 实际测试与检查

本轮验收总计 **481项不同测试通过**；不是历史1261项全量重跑。

| 实际命令 | 结果 |
|---|---|
| `python -m unittest discover -s tests/engineering -v` | 12通过 |
| `python scripts/ci/run_backend_tests.py` | 441通过；1条真实缓存Embedding测试明确排除 |
| `python -m pytest tests/investigation_api/test_tcp_chain.py tests/investigation_api/test_live_chain.py -q`（backend目录） | 5通过：新增TCP3条、既有TestClient2条 |
| `npm --prefix frontend test` | 23通过 |
| `python scripts/ci/check_contracts.py` | 42操作、5组PythonSchema、40个合成对象校验通过 |
| `python scripts/export_investigation_api.py --check` | 10份导出一致，无修改 |
| `node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json` | 退出码0，语义检查通过 |
| `node scripts/ci/check_frontend.mjs` | 17个已有JS文件语法通过；当前前端没有应用build命令 |
| `python backend/scripts/probe_investigation_http.py --timeout 30` | 退出码1；真实默认Mock未就绪被正确报告 |

新增无数据库测试18条（已包括在441中），TCP3条（已包括在5中），不重复累加。两组pytest套件各有1个现有Starlette/AnyIO弃用警告，共2条；没有本轮验收失败项或静默跳过。

独立审查发现检查工具遇到非法命令参数时可能保留旧成功摘要。已先复现，再修复参数解析错误路径，并实际运行3条新增回归：模式拼写错误、超时值非法、未知参数均返回退出码2并覆盖指定摘要为失败，不回显任意参数值。交接包中“未运行tsc”的过期说明也已更正；本轮契约语义检查退出码0。

独立复查确认两项初审问题均已解决，未发现新增阻断问题。仓库路径检查、暂存区敏感信息扫描、包清单哈希和ZIP逐字节一致性检查通过。交付为 [PR #8](https://github.com/shuabirfana-a11y/AegisAI/pull/8)，尚未合入main；GitHub CI以该PR最终提交的三项检查为准，不能借用PR #7的历史CI。main合并仍需负责人对本PR确认。

## 8. 当前限制与停止范围

真实模型尚未配置；受控成功链不代表真实模型可答任意问题。当前开发主体无登记资产，固定真实来源查询没有虚构asset_id。队友UI完成度仍需团队确认；独立人审标准答案0/49，不能发布准确率。

仍无SSE/WebSocket、分布式队列、自动续跑、多用户登录或公网域名适配。现有7个旧写操作继续受本地代理限制。本轮不改这些能力。

本阶段结束后停止。下一阶段可以授权真实模型固定样本联调；前端队友按当前公共契约接线；人工成员独立制作/复核Ground Truth。正式评测与公网部署分别等待授权。
