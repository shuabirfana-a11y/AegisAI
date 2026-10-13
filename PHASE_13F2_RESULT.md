# Phase 13-F.2 结果报告

**本轮输入适配、失败归因、最小实现和限定 5 题诊断已交付；Planner 稳定化验收未通过，正式 39 题实验条件尚未恢复。**

项目为 AegisAI（ICT 命题九），不是 SentinelGraph。没有更换模型、修改人工标准答案、执行 39 题正式重跑或计算新准确率。

## 1. 原 35 题失败分类

逐题使用原实验保存的 Planner 输出和所有尝试错误，不重新请求模型。完整记录：`evaluation/planner_failure_analysis/phase13f2/failures35.jsonl`。

| 主分类 | 数量 | 依据 |
|---|---:|---|
| A：输入信息不足 | 5 | 原题刻意未提供版本，必须保留 INPUT_REQUIRED/不确定 |
| B：模型计划错误 | 8 | 提供版本和实际资产，但模型遗漏资产步骤或改写作用域参数 |
| C：Task Contract 缺失 | 0 | 未观察到必须新增任务类型的证据 |
| D：评测输入适配错误 | 22 | 10 个风险题原资产版本漏传；12 个总览题被错误当成部署资产分析；F.1 已修 |

类别存在多因关系：35 题均有模型不满足现有契约的表现，D/A 不能被理解为排除 B。原终止错误为 VERSION_INPUT_REQUIRED 4、ASSET_LOOKUP_REQUIRED 8、TOOL_INPUT_INVALID 11、COMPONENT_SCOPE_MISMATCH 10、QUERY_SCOPE_MISMATCH 2。首个错误不等于唯一根因。

原另外两题来源冲突和两题 UNKNOWN 记录未删除。两题 UNKNOWN 与标准答案不一致不是 ID/hash 匹配失败。

## 2. 修改内容和输入契约

新增 evaluation 侧 BenchmarkQuestionContract，仅检查原 Question 输入和真实资产绑定。区分 READY / INPUT_REQUIRED，缺版本仍为空；targets 容器异常返回受控错误。不同题型字段映射见 `docs/phase13f2/BENCHMARK_QUESTION_CONTRACT.md`。

Planner 使用 v5 通用约束提示和作用域 JSON Schema：工具参数绑定真实 target、component/version、asset_id 及原 query；版本缺失时不提供版本工具调用；工具分支共享本地 `$defs`。不自动生成任务，不补资产/版本，不改原 Validator、角色权限或 Runtime。

Schema 和提示约束不保证模型服从。当前提供方沿用 json_object 模式，仍由 Gateway 和原 Validator 拒绝不合格输出。

## 3. Conflict Artifact 和核验交接

新增内部、不可变 ConflictEvidenceArtifact，引用原父 Artifact、Claim、Evidence，保留 CANDIDATE 和缺源说明。完整冲突/引用继续保留原处，用 canonical hash 和索引避免 JSONB 键排序问题及重复载荷。

阻断依赖的完整冲突观察可经 VERIFY_ONLY 交给独立 Verifier；原 BLOCKED/WAITING_REVIEW 状态、错误和 Gate 标准保留，新分支不运行风险分析。原完整冲突的 CONTINUE 路径保持既有行为。公开 VerificationArtifact、8 个调查 API、TypeScript/OpenAPI 均未变化。

本轮真实冲突题在 Planner 阶段失败，因此仅自动测试验证了新交接能力，**没有完成该真实场景的核验闭环验收**。

## 4. 冻结环境与隔离

- 实现提交：`d623a5d2752fdca8707754ae9b19a7a9b29f007e`；分支 `codex/phase13f2-planner-contract`。
- 原模型 Qwen2.5 / `aegisai-qwen25-planner:latest`，manifest `sha256:15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16`，未修改制品。
- temperature=0，timeout=40s，max_output_tokens=4096，原 structured_mode=json_object。提示版本 investigation-plan-v5。未回退 Mock；答案仍为原确定性模板。
- 新隔离库仅复制原来源图，不复制原运行/资产/Gold；4 个中性随机名称的演示资产来自题目输入，不是企业扫描数据。
- 5 个 HTTP 调查，10 次正常 Planner 尝试。Gold 只用于准备阶段确认样本已获批准，未传 Prompt、Context、Retrieval 或工具。
- 523 个受保护文件哈希未变化，覆盖原 Gold、原实验归档、评分、Runtime 和规则文件。模型 Gateway embedding 测试配置仍为 mock；这不是更换 Planner 模型或混入 Mock 答案。

完整冻结、实际资产登记和请求预检见 `evaluation/planner_failure_analysis/phase13f2/`。真实请求/响应、原始模型文本、私有 Planner 审计的脱敏摘录和 Runtime 读取结果见 `evaluation/failure_analysis/phase13f2/diagnostic5/`。

## 5. 五题真实 HTTP 结果

| 场景 / 题号后缀 | Planner | Runtime / Gate | AnswerEnvelope | 根因 |
|---|---|---|---|---|
| 漏洞事实 / 53q9-facts | 拒绝 | 未进入 | FAILED | 首次把证据工具放入错误任务角色；重试改写原检索 query，被 Schema 拒绝 |
| 版本影响 / 935w-affected | VALIDATED | 任务 SUCCESS；REPLAN_REQUIRED | INCOMPLETE | 两个任务重复 get_vulnerability，产生两个同目标候选根 Artifact；交接无法唯一选择 |
| 资产风险 / 53q9-risk-affected | 拒绝 | 未进入 | FAILED | 两次均重复 JSON `type` 键，被 strict_json 正确拒绝；原始文本保留 |
| 来源冲突 / c67j-affected | 拒绝 | 未进入 | FAILED | 两次均重复 JSON `type` 键，未进入冲突核验 |
| 缺版本 / 53q9-unknown | VALIDATED | input_required 等待；REPLAN_REQUIRED | INCOMPLETE | 不猜版本、不把未知当安全；缺核验/分析结果，Gate 保持阻断 |

确切调查、Planner、Runtime、Artifact 和 Integration ID 已保存在每题 JSON 与审计文件。2 个合法计划不能解释为语义正确，也不能作为统计稳定率。无新的正式评分；原 39 题严格匹配结果未改写。

## 6. 回归与审查

历史 1426 项只是此前记录。本次新增 18 项后端控制和 11 项评测侧控制，均实际运行。

| 实际检查 | 结果 |
|---|---|
| CI portable 后端 `python scripts/ci/run_backend_tests.py` | 549 passed，1 明确 deselected（缓存真实 Embedding 项），1 AnyIO 弃用 warning |
| 评测侧 `python -m pytest tests/aegisbench -q` | 126 passed |
| 全量后端 `python -m pytest -q` | 1416 passed / 31 failed；运行期间 Runtime 的提交式合成数据与旧计数测试共库，造成残留 |
| 全新独立计数测试库 `python -m pytest --lf -q` | 上述 31 项全部通过，1 warning；未删除原库或历史记录 |
| Contract/OpenAPI 校验 | PASS：42 HTTP operations、40 个合成对象；调查导出 10 文件一致，无导出改写 |
| 工程检查 `python -m unittest discover -s tests/engineering -v` | 18 tests，OK |
| 只读独立修复复审 | 26 项控制通过；四项 Important 问题关闭 |

不能把分隔后的回归写成“同一次全量 1447 项全绿”。完整原始测试输出保留于本机 `work/phase13f2/`；交付包测试凭据保留命令、真实摘要、失败原因和复跑结果，不把工程测试当准确率。

初次数据库测试缺少专用测试库、首次冲突快照回读失败、审查的 RED 测试及后续修复记录也保留；没有用删测试、修改业务规则或标准答案解决失败。

## 7. 修改文件

业务边界内增量：Investigation planner.py/planning.py/roles.py + 新 v5 Prompt；verification conflict_evidence.py/schemas.py/snapshot.py；orchestration handoff.py/service.py；evaluation question_contract.py/http_investigation.py。

新增上述三组后端测试与 Question Contract 测试；更新提示版本断言、授权源文件哈希断言、历史冻结配置兼容断言和 portable CI 测试清单。旧冻结配置、原提示 v4、Runtime、Validator、Risk/Gate 规则、Gold、Evaluator/Metrics 均保留。

分类、契约、冻结、五题原始记录、审查及报告为本次新增文档/分析交付。精确文件清单以 Git 提交 diff 和交付包 CHANGE_MANIFEST.json 为准。

## 8. 验收与停止

已交付：35 题逐题归因、输入契约、范围内最小适配、结构化冲突观察、边界回归、5 题真实诊断。

未通过：Planner 真实输出稳定性、真实冲突题核验闭环、完整正向调查回答。**formal_evaluation_conditions_restored=false，不能启动 39 题正式实验。**

下一轮若获授权，优先限定处理：重复 `type` 字段、角色对应工具示例、单目标唯一根调查的模型侧约束。保留 strict_json/角色验证/唯一 Artifact 交接标准；不改 Gold、评分或 Gate。缺版本场景的阻断继续保留。

本轮按五题上限停止，不继续调模型/提示、不执行更多真实题或 39 题正式评分，也不进行部署。提交草稿 PR，不自动合并。
