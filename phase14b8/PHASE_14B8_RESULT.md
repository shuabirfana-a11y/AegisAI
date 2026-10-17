# Phase 14-B8：49 题业务正确性诊断与最小修复

日期：2026-10-16。项目：AegisAI，ICT 命题九。仅本地保存，**没有推送 GitHub、创建 PR 或合并**。

## 1. 结论

49 题只有 3 题整题匹配，主要不是模型最后推理错误，也不是程序无法运行。现有链路缺少可适用的主来源证据，部分来源事实没有进入正式 Claim，另有并列影响范围丢失分区信息的问题。字段匹配也只有 **11/94（11.70%）**，不能把低分全部解释成严格整题评分。

**第一优先节点是 Evidence → Claim 的来源、组件身份和完整事实绑定。** 本轮只对该层做一个可验证的局部修复：接入已存在引用中的 LangGraph 官方仓库公告，保留其版本、CVE、组件及 CVSS 原文证据。不调整模型、Prompt、Risk、Verification 判断规则、Gate 或评分器。

## 2. 原 49 题真实基线

| 项目 | B7 已保存结果 |
|---|---:|
| 人工 APPROVED | 49 |
| 取得技术结果 | 42 |
| NEED_CONTEXT | 5 |
| 范围不支持 | 2 |
| 程序失败 | 0 |
| 严格整题匹配 | 3/49 |
| 原计分字段匹配 | 11/94 |
| 拆分 CVSS score/vector 后原子字段匹配 | 11/104 |
| CVE | 2/5 |
| affected | 4/27 |
| patch_status | 2/10 |
| risk_level / priority | 各 1/10 |
| priority_asset_ids | 1/6 |
| CVSS v3 / v4、CWE、summary、PoC | 各字段 0 匹配 |

字段口径直接读取金标 expected_answer，使用原评分器的精确比较；没有为产品、版本范围、修复版本等未标注维度另造金标。原子字段进一步拆分 CVSS 对象的两个现有子字段，属于诊断口径，不替换正式指标。

人工语义正确率、Evidence Support、Hallucination Rate 仍为 **PENDING**，不能用程序引用校验替代独立人审。

## 3. 每题唯一主断点

| 首个可测阻塞节点 | 题数 | 含义 |
|---|---:|---|
| Evidence，G | 20 | 缺可适用主来源/独立佐证，未完成负向 PoC 证据检索，或存在尚未解决的真实范围差异 |
| Claim，C | 10 | 5 道事实题缺 CWE/摘要等正式事实 Claim；5 道 commit 题缺专门补丁关联 Claim |
| Impact Scope，B | 7 | LangChain 并列影响范围和对应修复信息被置于同一未限定分区，形成跨分区冲突 |
| Input，H | 5 | 原始输入没有版本；合法 NEED_CONTEXT 与金标 UNKNOWN 的表达/准入契约不同 |
| Risk，D | 2 | vLLM 影响判断正确；风险/优先级的既有策略与 benchmark-reference-triage-v1 不一致 |
| Unsupported Scope，I | 2 | 跨公告资产批次未受支持，未编造结果 |
| 整题匹配 | 3 | vLLM affected、fixed、multihop |
| 合计 | 49 | 每题只计一次，后续 Risk/Answer 不重复算根因 |

这里统计的是**阻塞节点**，不意味着 20 道 G 类都是软件错误。包括 5 道未获得明确负向 PoC 检索凭据的题，以及 5 道原来源范围差异未消解的版本/风险/多资产题。不能把它们统一改成 CONFIRMED。

分类依据为真实 Schema、47 个封存上下文、12 份原始来源及实际中间产物。详细字段、原始片段、来源等级、时间、Claim/Evidence 关联和每题主断点见 `docs/phase14b8/field-level-analysis.json`。语义支持仍待人审。

未发现满足 J 类规定条件的“最终模型推理错误”案例：最终核验、风险和答案组合是确定性规则。本结论不表示 Planner 的所有行为都正确。

## 4. 典型事实链与次要问题

- **LangGraph**：OSV 与 GH 数据库记录虽有版本和 CVSS，但来自同一公告谱系。已有官方仓库链接未被 Vendor 采集白名单识别；原核验因此保持 PENDING。不能把两个转载当成两个独立来源。
- **PyTorch 2025 公告**：官方记录的包名为 `pytorch`，库存发行包为 `torch`。目前没有足够的同一发行包身份证明；本轮未强行增加别名。官方该记录的 CVSS 字段为空，不能从另一条来源拷贝后冒充厂商确认。
- **LangChain**：原始文档同时记录两个范围/修复配对，当前归一化没有保存可消费的分区信息。不能通过移除冲突或硬编码版本判断解决；本轮保留。
- **vLLM 风险题**：affected 与 NOT_AFFECTED 正确。LOW 金标与 MEDIUM 既有风险策略不一致；MONITOR 金标与 DEFER 的 API 策略不一致。不能用改大小写或降级 Risk 来装作修好了。
- **事实输出**：即使某条 CVSS 在内部 CONFIRMED，`project_answer()` 仍没有 CVSS 字段映射；公开值过滤也不包含 vector。这是次要 E 类契约问题。本轮没有同时改输出层。
- **PoC/Patch**：未发现候选并不自动证明 NO_EVIDENCE；固定发布版本也不等于 commit 正确性已确认。现有适配把 fixed_versions 投影为 CONFIRMED_FIX，不能拿来证明 commit 场景。
- **版本未知题**：NEED_CONTEXT 属于合法安全处理；原评分器将未启动任务记为 NOT_EVALUATED。本轮没有修改这一计分约定。

## 5. 保守/确认与多资产检查

27 道带 affected 金标的题，输出为 UNKNOWN 13、AFFECTED 2、NOT_AFFECTED 2、未输出 10；5 道未输出属于 NEED_CONTEXT。18 道题至少包含一个冲突 Claim。这些是观察状态，不重复加入主断点数量。

检查 32 个资产版本观察、5 个实际多资产批次的作用域、资产/版本绑定及子任务 Run/Artifact 独立性，**未发现机械跨资产引用错误**。同一漏洞 Claim/Evidence 在多个资产之间共享是合法的；资产观察和结果 Artifact 不能共享。

9 个资产子调查没有生成 Risk Artifact，均保留在 JSON 中，不能把空 Artifact ID 的重复当成跨资产污染，也不能把未生成风险说成已完成风险分析。

未发现本轮可以机械证明的“弱证据被直接改为确定受影响”问题；这不是生产安全性或语义支持率声明。实际输出的语义支持和幻觉仍需原复核人员逐条确认。

## 6. 实际最小修改

安全边界修复已在本地已有 b94dd7f 基线中保留：非法预填修复版本被排除，不能成为已确认修复事实、版本比较依据或修复建议；原始候选用于追溯。新增边界测试包含非法字符串、约束字符串、非字符串和版本字典序陷阱。

本轮业务只修改来源采集/解析层的三个文件：

1. `backend/app/enrichment/acquisition.py`：新增精确的 `VENDOR_LANGGRAPH → langchain-ai/langgraph` 白名单。未给予任意 GitHub 仓库官方权威。
2. `backend/app/enrichment/parsing.py`：声明对应发行包的官方仓库；只去除包名首尾空格；保留并校验公告原始 CVSS 向量与分数，异常保留 unresolved。
3. `backend/app/enrichment/enrichers/vendor.py`：漏洞级 CVSS 不需要包主语，避免被原包过滤误丢；包影响 Claim 仍需与既有目标发行包匹配。

来源是已有 OSV/GH 引用指向的真实官方公告，读取原文并保存 Hash，随后通过已有 VendorEnricher 回放入隔离知识库。原 12 份原始资料 Hash 不变，新增 1 份真实官方响应。**数据源回放与真实模型调用分开标注**：模型仍为真实本地 Qwen2.5，embedding 仍为原 Mock；没有假称实时扫描或全栈模型都是真实。

未修改 Agent、Runtime、Planner、Risk、核验规则、Gate、金标、评分公式、前端及数据库 Schema。未创建新 Agent 或新工具。

## 7. 8 题真实 HTTP 回归

同一选定 8 题做修复前与修复后两次完整 HTTP 调查，覆盖明确受影响、不受影响、UNKNOWN、NEED_CONTEXT、多资产、多来源、多跳和全部原三题匹配案例。

| 指标 | 修复前 | 修复后 |
|---|---:|---:|
| 严格整题 | 3/8 | 4/8 |
| 计分字段 | 4/12 | 5/12 |
| 程序失败 | 0 | 0 |
| 原三题保持正确 | 3 | 3 |
| Risk Match | N/A | N/A |
| Evidence Support / Hallucination | PENDING | PENDING |

本组没有 risk 类型金标题；实际中间风险记录已保存，不另外造风险金标。全部已启动任务经真实 Planner、Runtime、专业 Agent、Gate、AnswerEnvelope；缺版本题保持 NEED_CONTEXT，未启动模型任务。

新增通过的 LangGraph 题：**UNKNOWN / REPLAN_REQUIRED → AFFECTED / HIGH / PASS_WITH_WARNINGS**。五类来源绑定 Claim 均通过原核验规则。另对同一封存上下文做只读对照：仅删除新增官方证据，核验从 CONFIRMED 回到 PENDING。该对照不调模型、不调 API、不写数据库、不评分，确认改善来自证据路径，不是阈值放宽。

8 题是开发回归集合，不能把 4/8 外推为全量 49 题准确率。原 B6/B7 结果未覆盖。

## 8. 本次实际验证

| 命令 | 实际结果 |
|---|---|
| `python -m pytest -q backend/tests/test_phase14b8_primary_evidence.py backend/tests/agents/verification/test_impact_normalization.py backend/tests/agents/verification/test_rules.py backend/tests/agents/analysis/test_rules.py`（独立测试库） | 79 passed |
| `python -m pytest -q backend/tests/test_phase14b8_primary_evidence.py backend/tests/test_phase7_enrichers.py backend/tests/orchestration/test_legacy_compat.py::test_old_api_and_business_source_hashes_are_unchanged`（独立测试库） | 28 passed |
| `python scripts/ci/run_backend_tests.py` | 716 passed，1 个原便携模式排除项，1 warning |
| `python -m pytest -q tests/aegisbench tests/evaluation` | 138 passed |
| `python scripts/ci/check_contracts.py` | PASS；56 HTTP operations；没有修改导出 |

这些组存在重叠，不能相加声称新增测试总数。新文件为 12 项测试；最初测试真实呈现 7 failed/4 passed，修复后通过，另补充真实数据库持久化测试。历史 1751 全量通过属于 B7；被用户停止的旧 guard 全量复测不记为本轮通过，也不重新用工程测试数代表业务效果。

## 9. 是否继续 49 题

**8 题回归准入通过，值得另行冻结新版全 49 题；本阶段没有启动新 49 题实验。** 当前最新全量结果仍是 B7 的 3/49。本阶段完成的是逐题诊断、证据层局部修复与 8 题验证，不能宣称全量准确率提升。

完整复测需冻结新增官方证据后的知识库、代码文件 Hash、模型与 Prompt、资产输入、补查预算和原评分规则；保留独立 B8 目录，不覆盖 B7。基线 RAG-only 和 No Verification 仍为 NOT_IMPLEMENTED，没有对照提升声明。

## 10. 尚未解决与下一步唯一优先事项

唯一优先继续 **Evidence → Claim 的适用性与绑定完整性**，尤其取得有来源证明的发行包身份及官方影响范围；不能把 PyTorch 的 `pytorch` 自动等同 `torch`。剩余问题包括负向 PoC 证据、并列范围配对、CWE/摘要事实契约、CVSS 输出缺字段和风险策略差异。本轮没有同时修改这些层。

模型/Prompt 优化、改评分和降低 Gate 均不是这次数据支持的第一刀。没有进入 B9；没有自动关机；所有更改与交付包仅在本地。

## 11. 交付

`docs/phase14b8/` 保存逐字段 JSON/Markdown、错误分布、8 题回归集合、前后对比、源码 Hash 例外、冻结信息与主来源作用验证。

原工作区 `outputs/AegisAI_Phase14B8_Diagnosis_Package/` 提供可直接打开的文件夹，内含 `phase14b8/`、测试回执、逐题回归输出与实际官方来源原文。
