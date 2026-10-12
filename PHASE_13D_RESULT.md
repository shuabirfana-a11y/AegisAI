# Phase 13-D：AegisBench 完整调查评测准备

本轮先按负责人授权合并 [PR #12](https://github.com/shuabirfana-a11y/AegisAI/pull/12)，main 基线为 `59ea2a239556e70514ce19bba52141121a98d570`。本阶段只增加评测适配、测试和文档；没有修改业务实现或人工答案。

## 1. 评测架构与数据流

`Question → Approved 准入 → Investigation HTTP API → Planner / Runtime / 三专业 Agent / Gate → AnswerEnvelope → Prediction → 人工 Ground Truth / OutcomeAudit → 原 Metrics`。

新增 `python evaluate.py --mode online` 和 `--mode offline`；不传 mode 仍使用原候选框架入口。线上模式经原认证创建调查，有限轮询状态，读取 Trace、Artifact、Integration 和冻结答案；不直接调用模型、Agent、数据库或内部 Orchestrator。离线模式只读已冻结记录，核对报告、原生记录及题目/来源哈希。

## 2. 新字段与 Ground Truth 隔离

复用现有 Question / Annotation / Prediction / OutcomeAudit，不更改人工模板数据。显式库存绑定资产和组件 ID，原问题版本、目标不得被覆盖。公开 Artifact 中的 Version Observation、Impact Evidence、原生 Verification 状态和风险优先级进入记录；缺失字段不从标准答案补齐。

传给 HTTP 适配器的只有问题、输入上下文、显式库存绑定和准入 ID；标准答案只在最终评分器中比较。未知版本、冲突、失败和不支持的多资产/多目标保留；不会变为安全或 Gate 通过。

## 3. Metrics 与报告

复用原评分器：Answer Accuracy、Risk / Priority Accuracy、版本判断、Abstention Quality、流程覆盖与耗时。Evidence Coverage 和 Hallucination Rate 另需绑定本次输出的独立人工 OutcomeAudit，不能用系统自己的 CONFIRMED 或引用有效性代替。

输出 `report.json / report.md`、`predictions.jsonl`、`native-http-records.json`、`experiment.json` 和待审核输出清单，记录数据集、Git、评测器哈希、实际模型/Prompt、时间和配置。原生来源 UUID 保留原身份，不伪装成冻结语料证据 ID。

## 4. 本次实际测试

历史 1426 项属于 Phase 12-D.3；本轮没有重新宣称执行该完整历史集合。下列为本轮实际命令与结果，集合存在重叠，不相加为总测试数。

| 命令 | 本次结果 |
|---|---|
| `python -m pytest tests/aegisbench -q` | 84 passed；包含审查问题负例与实际 Schema 漂移检查 |
| 在 backend 执行 `python -m pytest -q tests/investigation_api` | 112 passed；包含新增 3 条完整 TCP 控制 |
| `python scripts/ci/run_backend_tests.py` | 531 passed，1 deselected（原 CI 明确排除的真实本地 Embedding 测试），1 框架弃用提示 |
| `python scripts/ci/check_contracts.py` | PASS，42 个 HTTP 操作、40 个合成对象 |
| `python scripts/export_investigation_api.py --check` | PASS，10 个原导出文件未改变 |
| `python scripts/export_bench_http_schema.py --check` | 9 组实际 Pydantic Schema 一致 |
| `python -m unittest discover -s tests/engineering -v` | 18 passed |
| `node scripts/ci/check_frontend.mjs` | 原生 JavaScript 检查通过 |
| `npm --prefix frontend test` | 23 passed |
| TypeScript 契约检查 | 通过；当前原生前端没有构建脚本，构建不适用 |

三个新增 HTTP 控制使用合成数据及 Mock 模型，仅证明工程链路：受影响场景 CONFIRMED / HIGH / PASS；版本未知 UNKNOWN / REPLAN_REQUIRED；来源冲突 CONFLICT / HUMAN_REVIEW_REQUIRED。原 Planner 和三 Agent 都产生真实执行记录，新 Observation / Evidence 已被核验消费。脱敏 ID 与状态见 [HTTP_CONTROLS.json](docs/phase13d-e2e/HTTP_CONTROLS.json)。本阶段没有重新执行真实模型准确性实验。

## 5. 49 题实际准入

线上准备和离线回放均实际运行：49 条候选、0 条 APPROVED；没有创建网络客户端或调用模型，质量指标为 null / NOT_EVALUATED。[准备记录](docs/phase13d-e2e/PREPARATION_RECORDS.json)。外部 DRAFT 标注包仍需独立人审，未自动导入或批准。

原 `backend/app`、现有题目/标注/来源非 Markdown 文件共 352 个保持字节不变，[冻结检查](docs/phase13d-e2e/PROTECTED_FILES.json)。只追加 Ground Truth 字段说明文档。

## 6. 修改文件

- `evaluation/bench/http_investigation.py`：完整 HTTP 调查、原生响应校验和输出投影。
- `evaluation/bench/e2e.py`、`evaluate.py`：人工准入、Online / Offline、冻结回放和报告。
- `tests/aegisbench/test_http_investigation.py`、`test_e2e.py`、`test_http_schema_export.py`：输入隔离、错误、未知、回放和 Schema 控制。
- `backend/tests/investigation_api/test_bench_http.py`：原服务真实 TCP 三场景工程控制。
- `scripts/export_bench_http_schema.py`、`evaluation/contracts/investigation-http-eval-v1.schema.json`：实际 Schema 导出和漂移检查。
- `evaluation/ground_truth/schema.md`、`docs/phase13d-e2e/`、`CURRENT_STATUS.md`、本报告及 spec / plan：交付说明、实测记录和阶段状态。

## 7. 当前限制与下一步

独立只读审查提出 5 个重要问题，已在评测层一次修复，并通过新增负例 RED → GREEN：禁止绑定补入未知版本；核对原问题及完整资产条件；绑定实际 Artifact/证据引用；失败即时保留材料和模型标识；统一阻止各 Baseline 的 Mock 输出获得正式分数。另将“有记录但未发出请求却显示 http_executed”重新定级为重要报告真实性问题并修复。[审查处理](docs/phase13d-e2e/REVIEW.md)。

1. 人工 APPROVED 为 0，未进行正式准确率实验。
2. 普通 RAG 与无 Verification Agent 的独立对照仍未接入本轮入口；明确 NOT_IMPLEMENTED，不添加生产跳过核验开关。不能宣称三方实验已完成。
3. 各对照的归一化数据、库存和来源一致性尚未独立证明，不能宣称公平消融。旧 native adapter 的准入限制不变。
4. 当前单资产调查不覆盖所有候选的多资产聚合问题；部分旧参考字段没有原生交付映射，缺失保持缺失，不修改人工答案迎合模型。
5. 原优先级 P1/P2/P3/DEFER/REVIEW_REQUIRED 与候选 triage 分类不等价，不做静默转换。
6. 版本/风险题必须绑定操作者真实拥有的库存；环境/暴露/版本需与封存观察一致。不创建企业扫描数据。
7. 公开 Trace 仅列主要交付 Artifact，资产子任务源 UUID 当前不能逐个展开验证；核对其原 run / 成功任务和观察语义，不声称存在尚未公开的查询 API。

本阶段完成评测入口与准备交付后停止。等待人工双人批准和后续实验授权；不进行正式评测、PPT 或公网部署。本轮新 PR 不自动合并。
