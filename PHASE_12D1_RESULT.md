# Phase12D.1 真实模型Planner稳定化与调查闭环验证

日期：2026-10-12。项目：AegisAI / ICT命题九 / 奇安信。

**本阶段验收通过：选定本地Qwen2.5配置完成20/20合法规划，并通过两次真实HTTP三Agent→Gate→Answer闭环。验收范围是固定问题下的规划协议与有界情报概览；版本/资产业务场景仍未通过Gate。Qwen3.5未通过规划验收，不推荐用于当前演示。**

没有修改Runtime、两种Validator、专业Agent、Risk/Gate规则或评测框架；没有放宽任务/工具白名单、修补模型输出、隐藏Mock回退、运行正式AegisBench或公网部署。

## 1. 模型与运行配置

Windows原生Ollama v0.40.3，RTX5060 Laptop约8GB显存，内存约15.2GiB。复用已安装模型，没有下载更多模型或依赖。

| 项目 | 最终配置 |
|---|---|
| Provider | openai_compatible / 本机Ollama |
| 推荐文本模型 | aegisai-qwen25-planner:latest，Qwen2.5 7B instruct Q4_K_M |
| 对照模型 | aegisai-qwen35-planner:latest，Qwen3.5 4B |
| 模型别名摘要前缀 | Qwen2.5 15aaf3fda3b8；Qwen3.5 c54d555f81c7 |
| 上下文 / 输出上限 | 16384 / 4096 |
| 温度 / 思考设置 | 0.0 / reasoning_effort=none |
| 输出方式 | json_object；仍由Gateway执行完整JSON Schema/Pydantic验证 |
| 预热后Provider超时 | 20秒；Planner原有最多两次尝试 |
| Embedding | 仍为Mock；未评价向量语义效果 |
| 最终实跑时间UTC | 2026-10-12T06:49:46.526020Z—07:05:32.890838Z |

配置：[local-real-profile.json](demo/phase12d1/local-real-profile.json)。启动及复现：[README](demo/phase12d1/README.md)。没有模型API Key，认证只在本机进程中。

## 2. 根因与修复

旧Phase12D探测调用通用五任务 `LLMTaskPlanner`；实际HTTP调用三任务 `InvestigationPlannerAdapter`。前者的Schema修复没有传到后者：InvestigationTaskCandidate直接继承TaskContract，模型侧Schema允许错误的 `input_data.target`，原Runtime仍正确拒绝它。

本轮让InvestigationTaskCandidate复用既有PlannerTaskContract的结构Schema，同时保留自身三任务Literal。通过先失败后通过的测试，确认直接参数、空steps、额外工具字段和未知任务都被拒绝；没有改变执行契约或Validator。

小范围提示修订依次解决：把已知CVE误认为缺少输入；漏写 `type`、混淆 `task_type` / `required_fields`；擅自缩短semantic_search.query。最终提示为 `investigation-plan-v4`。模型输入新增按角色列出的可缺字段、确定排序的工具Schema、从原始Scope复制的允许参数值，模型仍自己选择计划。

没有增加输出修复层。外层 `tasks` 是DAG任务，内层 `input_data.steps` 是工具调用，两者不会被重命名或补齐。

实际HTTP白名单仍为 vulnerability_lookup、evidence_search、asset_lookup。版本检查仍用已有只读 `inspect_component_version`，风险分析仍由下游Risk Agent完成；未新增version_match/risk_analysis规划任务。

## 3. 固定问题集与统计定义

固定问题：[cases.json](demo/phase12d1/cases.json)。三类分别是CVE-2025-32434事实概览、PyTorch2.5.1版本影响、多步骤Evidence/Claim记录调查。

最终每模型20次独立、持久化的实际Investigation Planner调用，分布7/7/6；另外每模型三类各一次真实HTTP完整调查。规划稳定性分母20，HTTP验收分母3，Provider尝试另计。未执行Runtime的规划不计入HTTP成功率；每次使用新幂等键，无筛选失败或复用旧成功。

这些重复只覆盖三个固定问题、一个真实CVE，温度为0，不支持泛化准确率结论。版本条件是测试输入，没有伪造真实资产库存。

## 4. 最终稳定性结果

| 指标（逻辑规划次数分母20） | Qwen2.5 | Qwen3.5 |
|---|---:|---:|
| JSON成功 | 20/20，100% | 13/20，65% |
| Schema通过 | 20/20，100% | 7/20，35% |
| 原Task/DAG/权限验证通过 | 20/20，100% | 0/20，0% |
| 实际Provider尝试次数 | 20 | 40 |
| Provider尝试级Schema通过 | 20/20，100% | 7/40，17.5% |
| 平均规划耗时，含持久化 | 11.186秒 | 26.413秒 |
| 有返回统计的Token总数 | 112405 | 192054 |

没有文本返回的超时保留在次数分母中。Qwen3.5主要拒绝原因是MINIMUM_CRITERIA_MISSING、SCHEMA_VALIDATION_FAILED、TIMEOUT；没有静默切换模型或Mock。

| 独立HTTP三个场景 | Qwen2.5 | Qwen3.5 |
|---|---:|---:|
| 合法规划 | 3/3 | 0/3 |
| 三Agent/Artifact/Gate/Answer均有实际输出 | 3/3 | 0/3 |
| Gate验收通过 | 2/3，66.67% | 0/3 |
| 平均完整探测耗时 | 32.599秒 | 25.662秒 |

“有输出”包括失败Artifact或等待复核状态，不等于所有安全结论得到确认。只把PASS/PASS_WITH_WARNINGS作为验收通过。HTTP样本只有3次，66.67%不是统计上的可靠性或安全准确率。

完整回执：[stability.json](docs/phase12d1/stability.json)。旧v2/v3每模型各20次HTTP失败对照也全部保留：[baseline-cohorts.json](docs/phase12d1/baseline-cohorts.json)。导出时只重新读取原持久化审计，重新模型调用为0，未改写原始报告。

## 5. 完整真实链验证

推荐模型事实场景：

| 引用 | 实际ID |
|---|---|
| Investigation ID | 77b15e30-8f51-442f-ae03-d6c0b588f644 |
| Planner Run ID | 1750ae75-3e16-4d1b-8b60-1c83594a49f6 |
| Investigation Artifact | ff0af038-41f8-4937-88e7-441ce42a885c |
| Verification Artifact | 4b8196a0-98f4-4005-b68d-b905f5c0ccbe |
| Risk Artifact | 36879567-0820-4bf5-ac6e-3d92c4c4b383 |
| Integration ID | 73e8e448-910b-4368-9a05-cd9def71d223 |
| Answer ID | 559c8184-e883-551f-a8ab-e423b5ef5fcf |
| Gate / Answer状态 | PASS_WITH_WARNINGS / COMPLETE_WITH_WARNINGS |

另一条多步骤成功调查ID：`5b74f62c-a306-4bc6-9d39-a01fdbfbd0e9`。两条成功链的三Agent Run IDs、工具回执、Artifact IDs及Gate检查见 [http-chain-receipts.json](docs/phase12d1/http-chain-receipts.json)。

实际通过原有八个HTTP接口运行，不是TestClient、MockTransport、预制Artifact或假Gate。Trace确认REAL / PERSISTED_PLANNER_CALL；来源是已有真实情报库。两条成功链保留Verification/Analysis的WAITING_REVIEW和未知项，原Gate只允许有界概览验收，未强迫确认影响版本或风险。

再次读取Answer结果一致，新增Planner调用0。AnswerComposer仍为原确定性冻结投影，不重新调用模型生成事实。临时HTTP服务已结束，模型服务保留。

## 6. 测试、审查与失败核算

历史1261是历史工程验收，不当作本轮执行结果。本轮各集合存在重叠，不相加称为独立测试总数。

| 实际检查 | 结果 |
|---|---|
| 广泛后端回归（v3时点） | 891 passed，23 warnings，752.81秒 |
| 最终代码可移植后端基线 | 502 passed，1 deselected，10.82秒 |
| 最终针对性含真实PostgreSQL/合成TCP回归 | 59 passed，19.64秒 |
| 工程启动与失败保护测试 | 18 passed |
| OpenAPI/Pydantic/Mock导出一致性 | PASS，42 HTTP操作 |
| 调查API导出检查 | PASS，10文件，无改写 |

最终源码新增39项合成协议/Schema/失败/存储/TCP测试，真实模型测量单独记录。唯一明确排除项是缓存真实Embedding测试，未把它算作通过。广泛回归不是对最终v4源码重新执行891项；最后改动的规划、探测、兼容、取消、计数和存储路径由最终502/59集合覆盖。

实际命令：

```text
python backend/scripts/probe_planner_stability.py --planner-stability --model aegisai-qwen25-planner:latest --model aegisai-qwen35-planner:latest --output work/phase12d1/stability-final.json --ollama-executable <本机已有Ollama>
python -m pytest tests/runtime tests/planner tests/agents tests/integration tests/orchestration tests/investigation_api -q
python scripts/ci/run_backend_tests.py
python -m unittest discover -s tests/engineering -v
python scripts/ci/check_contracts.py
python scripts/export_investigation_api.py --check
```

广泛回归与针对性pytest从backend目录运行，本机数据库地址只配置在环境中；原始日志在忽略目录work/phase12d1。

一次独立全分支审查没有发现生产安全边界改动，发现四项探测工具问题：旧成功报告残留、中断次数遗漏、HTTP超时遗漏已发起尝试、模型任务ID未走脱敏。均先复现失败，再在一轮修复中处理；实际PostgreSQL中断测试也确认本次独立Planner审计标为PLANNING_FAILED且未创建Runtime。没有再次委派审查，没有未处理Minor。

现在启动前先写新报告；运行前留存进行中条目/本次审计ID；异常保留已完成尝试并标明核算是否完整；超时读取本次拥有的Planner审计；公开元数据复用原API脱敏。缺失计数明确为下界，不冒充完整的0次。私有审计及任务ID不改写。

## 7. 修改文件与兼容性

- 生产规划：planning.py、planner.py、roles.py；保留v1，新增v2/v3/v4提示文本。
- 探测：backend/scripts/probe_planner_stability.py；固定问题与本轮profile/README。
- 测试：test_model_schema.py、test_planner_stability.py、test_stability_failures.py、test_stability_tcp.py；原test_planning.py只更新提示版本断言。
- CI/兼容：scripts/ci/run_backend_tests.py新增离线测试；test_legacy_compat.py加载独立Phase12D.1精确哈希例外，历史基线及Phase12D例外不变。
- 文档：本报告、CURRENT_STATUS.md、docs/phase12d1实跑/审查回执。真实HTTP Schema与TypeScript契约没有变动。

## 8. 当前限制

1. 版本场景调查ID `06cc6ede-6437-487b-a7d0-c9fd3410a4ca` 为Gate FAILED。原检查包含ASSET_SCOPE_MISSING、OBJECTIVE_VERSION_MISMATCH、OBJECTIVE_PACKAGE_MISMATCH及复核/分析等待。尚未形成可信资产版本影响闭环，不能声称版本/风险功能已全部真实验收。
2. Qwen3.5没有合格计划，不自动选择或回退它。推荐配置只对固定问题有本轮证据。
3. 真实来源是已采集本地数据，不是实时重新爬取；仅一个CVE，未评价事实准确率、多跳准确率或泛化能力。
4. Embedding仍为Mock；人工Ground Truth仍未独立复核批准，未做正式AegisBench。
5. 前端工作台、公网网站、云服务器及新机器环境没有在本阶段验收。临时端口关闭后需按说明启动后端，不能承诺当前8000/8769正在服务。

## 9. 下一步建议与停止

下一次单独授权优先查清版本/资产Scope交接和证据等待原因，保持Gate拒绝；随后由队友按既有API展示REAL模式、未知项和来源。等人工标准答案获独立批准后再安排正式评测。

本阶段按选定模型稳定规划及至少一次真实有界调查闭环完成，停止开发。没有开始正式评测、公网部署、更多模型接入或Agent扩展。
