# Phase12-D.2 真实场景扩展验证与失败模式分析

日期：2026-10-12。项目：AegisAI / ICT命题九 / 奇安信。

**已完成失败定位、五类真实HTTP场景以及两项独立诊断复查。旧版本问题不是JSON格式失败：合法计划执行了版本检查，但资产上下文缺失、单Artifact交接和影响证据不足导致阻断。扩展场景还暴露出Planner的等待预算与范围约束问题，不能把之前固定三问的20/20推广到新业务。**

本轮没有修改backend/app、Planner提示、Runtime、三Agent、Risk/Gate规则或Evaluation Runner。类型C业务问题只报告，相关开发暂停。新增内容是诊断脚本、固定输入、测试和文档。

一次独立审查另发现并修复诊断脚本的空Artifact收集和库存owner授权检查。修复后只读重取既有审计，没有重新模型推理。原资产测量使用受控本机示范库存并按库存owner设置临时授权，不作为真实用户鉴权验收；新脚本要求操作人独立配置owner并拒绝跨owner。

## 1. 当前模型与测量边界

沿用本地aegisai-qwen25-planner:latest，Qwen2.5 7B instruct Q4_K_M，Ollama/OpenAI Compatible Provider，investigation-plan-v4。原JSON Schema、三任务/只读工具白名单、最多两次尝试及Validation均保持。

初始五次按既有20秒Provider预算执行；诊断复查为40秒，仅是独立测试配置，不覆盖默认配置。仍为Mock Embedding。没有新增模型或依赖，没有正式AegisBench、人工答案填写或准确率评价。

两类真实测量分开保存：

- [初始五场景回执](docs/phase12d2/scene-receipts.json)：UTC08:51:19—08:54:18，5次逻辑调查、8次实际Provider尝试。
- [两项诊断复查](docs/phase12d2/followup-receipts.json)：相同模型及规划提示，2次逻辑调查、3次Provider尝试。

使用本地已采集来源；没有重新爬取或人工确认安全结论。资产场景全部为既有is_demo=true示范库存，不能据此证明真实服务器部署。

## 2. 初始固定场景

| 场景 | 固定输入 | 实际结果 | 是否到达Gate |
|---|---|---|---|
| 漏洞概览 | CVE-2025-32434，原已通过问题 | PASS_WITH_WARNINGS，有答案，保留待复核项 | 是 |
| 组件版本 | PyTorch2.5.1+CVE-2025-32434，无资产ID | 原Scope和证据缺口，FAILED | 是 |
| 资产风险 | 已登记Demo资产/组件ID+PyTorch2.5.1 | 两次模型TIMEOUT，PLANNING_FAILED | 否，gate_status=null |
| 证据不足 | 同一Demo库存+CVE-2022-45907，本地仅1 Claim/1 Evidence | 两次ASSET_LOOKUP_REQUIRED，PLANNING_FAILED | 否，未实际核验到“证据不足”阶段 |
| 来源冲突记录 | CVE-2026-9540，库内现有open版本冲突 | 两次COMPONENT_SCOPE_MISMATCH，PLANNING_FAILED | 否，不能声称Gate已确认冲突 |

五次中的三个规划失败都没有伪造Gate状态。JSON合法、工具成功、Artifact产生与可信业务结论是不同检查。

## 3. 成功案例与业务复查

本轮概览成功调查：`d6541956-d4b0-4448-a32b-39e7f8c01785`；Planner：`e9b96045-4d5b-4a08-b219-59ff7f7f2823`；Gate：`b2c3d2c2-dfae-46d3-b88b-eafb9eed874e`。实际三Agent和冻结AnswerEnvelope可读，读取答案没有新增规划调用。PASS_WITH_WARNINGS只支持已有事实概览和公开未知项，不确认资产风险。

资产复查仅改变本次等待预算，输入、模型、系统提示和规则不变。调查：`5927e120-b743-456f-9c42-a4680c810cde`；Planner：`a31ce3a6-0c03-4261-9ae4-c7e9e242fffd`。首个可读计划仍遗漏资产查询，原验证器拒绝；第二次合法计划进入三Agent业务链。资产快照RESOLVED，原ASSET_SCOPE_MISSING及包/版本FATAL不匹配消失，但Verification仍PENDING、风险UNKNOWN，Gate为REPLAN_REQUIRED。

| 资产复查引用 | 实际ID |
|---|---|
| Investigation Artifact | 9efc99f0-e402-49a4-aa4a-bbfb083b9c6c |
| Verification Artifact | 69f35993-1755-41a8-bcf5-bb82698cc680 |
| Risk Artifact | f0484dc0-ea37-48bd-8f7e-29b0aefbaa6f |
| Integration | 49c3251b-7ca8-4fda-b507-cf099153a11c |

冲突复查使用此前固定的多步骤资料查询模板，只替换CVE目标；未改Planner提示。调查：`13c42a8b-477e-484d-9606-1123b481f6dd`；Gate：`ba98d1ee-890c-43f5-836b-8f72378e33a2`。合法计划执行后存在候选冲突观测，核验和风险Artifact未完整产生；Gate以REQUIRED_ARTIFACT_MISSING、REQUIRED_TASK_INCOMPLETE、VERIFIED_EVIDENCE_MISSING等返回REPLAN_REQUIRED。候选观测数量不代表独立冲突数量，verified_conflict_count=0不能解读为已经排除了冲突。

复查没有替换初始失败、没有把等待或失败升级为Warning，也不证明新问题的Planner已稳定。

## 4. 历史与本轮失败定位

历史版本调查`06cc6ede-6437-487b-a7d0-c9fd3410a4ca`和本轮`ecb8797a-2a26-475d-a1a2-b7103e9bd405`均重复出现相同阻断。

历史计划包含get_vulnerability、inspect_component_version、get_evidence、get_claims；不含asset_lookup，因为输入确实没有asset_id。Risk Analysis本来是后端固定下游阶段，不是此三任务Planner可新增的任务类型，不能据此声称计划漏了risk_analysis。

历史基础Artifact`643b24a3-01c1-4247-bdd9-b26cf753a251`被选作单一核验来源；版本子任务的Artifact`fff43f41-5e07-47e2-a20e-91cafca683ec`保留有效的组件观察，却没有成为该交接输入。一个当前来源区间比较为IN_RANGE，其它表达仍UNKNOWN；这只是来源断言/区间比较，不等于独立核验确认影响。

四条AFFECTS_VERSION Claim均非CONFIRMED。排除原因包括RAW_OR_EXCERPT_INTEGRITY_FAILED、不可用或非当前来源、缺少合格独立证据以及不支持的版本表达；派生区间没有不可变Claim绑定证据时仍是Candidate。即使补资产，这些证据问题也不会自动消失。

## 5. Gate规则、Artifact与补充信息

每条原规则、等级、涉及Artifact和原引用保存在[evaluation/failure_cases](evaluation/failure_cases/README.md)。诊断不修改原生refs，不覆盖原Artifact。

| 原规则 | 实际原因 | 需补信息/后续方案 |
|---|---|---|
| ASSET_SCOPE_MISSING / REPLAN | component-only问题被解析为asset_impact_v1，但无asset_id | 合法资产/明确组件，或另行设计组件-only契约 |
| OBJECTIVE_VERSION_MISMATCH、OBJECTIVE_PACKAGE_MISMATCH / FATAL | 目标torch2.5.1与MISSING快照的null不相等 | 有效库存；缺失与真实不匹配的业务语义需单独审查，现等级不改 |
| REQUIRED_TASK_INCOMPLETE / REPLAN | 任务真实执行但WAITING_REVIEW，目标要求的结果未完成 | 完成所需证据；不能把WAITING_REVIEW当SUCCESS |
| OBJECTIVE_NOT_COVERED / REPLAN | 资产、版本影响、风险或优先级没有充分依据 | 受支持的版本区间、精确身份和独立证据 |
| UNRESOLVED_ANALYSIS / REPLAN | PENDING核验、未知风险与影响 | 合格Claim证据和正确库存，保留UNKNOWN |
| REQUIRED_ARTIFACT_MISSING等 / REPLAN | 冲突复查仅完成调查侧，后续核验/风险输入不足 | 审查冲突观察、依赖阻断和验证交接；不能跳过Verifier |

原decision规则FATAL优先于HUMAN/REPLAN，所以旧组件-only调查最终FAILED；这不等于它已经证明“受影响”。本轮未更改该优先级。

## 6. 缺失数据及是否需要修改

| 分类 | 本轮判断 | 本轮处理 |
|---|---|---|
| A Schema缺失 | 未找到解释旧Gate阻断的Schema缺失；旧/本轮版本Plan都通过原验证 | 不修改生产Schema |
| B 简单接口适配 | HTTP请求字段已进入原Scope，合法库存可RESOLVED；不是改字段名即可解决 | 不增加API或改变现有契约 |
| C 业务契约/交接 | 组件-only与资产目标耦合；分散版本观察和单Artifact核验交接；冲突后的后续阶段不完整 | 按授权边界暂停相关业务开发，只报告 |
| DATA | 四条影响Claim未充分确认，部分来源/表达/证据完整性有缺口 | 列出原证据/Claim ID，禁止猜答案或修补哈希 |
| 模型输出/预算 | 20秒资产超时；遗漏get_asset；缺组件Scope时模型尝试版本工具 | 保留原拒绝；40秒和固定模板仅作诊断，不永久改配置 |

业务数据只读前后七类数量保持：278漏洞、48 Claim、76 Evidence、7 ConflictRecord、5 Demo资产、205组件、268包身份。只新增本次正常调用审计，不改上述记录或人工Ground Truth。

## 7. 测试及数据真实性

新增诊断测试已先失败后通过，覆盖原UNKNOWN/FATAL保持、Gate未执行、原生停止原因、独立版本Artifact、资产充分但证据仍不足、候选/已核验冲突区分、继承观测去重、三种Artifact引用和脱敏。实际最终计数见[verification.json](docs/phase12d2/verification.json)，历史1261或Phase12D.1检查不算本轮执行。

审查修复新增七项实际复现：VERIFYING/ANALYZING有Run而无Artifact时保持为空并保留Run ID；单例读取异常不丢后续案例；独立owner缺失、跨owner、匹配以及资料查询临时actor。均先失败后通过。审查边界和处理见[REVIEW_RESOLUTION.md](docs/phase12d2/REVIEW_RESOLUTION.md)。

相关现有业务回归实际执行：

```text
python -m pytest tests/integration/test_rules.py tests/agents/verification/test_rules.py tests/agents/analysis/test_rules.py tests/agents/analysis/test_matching.py tests/orchestration/test_handoff.py tests/orchestration/test_contracts_scope.py tests/investigation_api/test_failure_diagnostics.py -q
python scripts/ci/run_backend_tests.py
python scripts/ci/check_contracts.py
python scripts/export_investigation_api.py --check
```

另以独立测试库的明确SYNTHETIC资料捕获原上下文，运行四项原Gate规则控制：充分上下文PASS、缺影响证据REPLAN_REQUIRED、明确冲突HUMAN_REVIEW_REQUIRED、缺资产值FAILED。[控制回执](docs/phase12d2/gate-controls.json)。这些控制使用明确Mock Planner，不计为真实模型/真实资产/正式评测结果，也没有修改持久化业务Artifact。

前端应区分PLANNING_FAILED和Gate失败；尚未产生Gate时不能显示伪造状态，按已有API的NOT_READY处理。UNKNOWN、PENDING、候选冲突和真实来源/Demo资产标识必须保留。现有HTTP Schema和TypeScript契约未改变。

## 8. 下一阶段建议与停止

下一阶段先审查业务修复方案：组件-only目标的独立契约；可追溯版本观察的交接和必要语义验证；冲突观察后的独立核验入口；合格影响证据的补采/关联。该方案需单独授权，避免为了通过而改变Gate标准。

本轮完成分析与扩展验证，停在这里。真实资产风险和来源冲突的确定性业务闭环仍未通过验收；不进入正式Benchmark、Prompt优化、更多模型或公网部署。
