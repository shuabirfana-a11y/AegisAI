# Phase 14-B7：影响范围证据与核验事实链结果

## 结论

影响范围已经进入新封存的 Verification Claim，并实际影响 Risk 和 Answer。真实 HTTP 中，vLLM 0.29.0 被判定受影响，0.30.0 被判定不受影响，均能回溯官方影响范围和修复约束；对应多资产结果不会串用版本。

但本轮 **49 题严格整题匹配仅 3/49（6.12%），风险等级匹配 1/10**。事实链修复有效，整体业务正确性仍不足。不能据此宣称达到比赛准确率目标，也不能把工程测试通过解释为安全答案正确。

完整原始结果、逐题事实链、来源片段和待签人工表单均已保留；停止本阶段，不继续新增功能。

## 1. B6 的 0/49 根因

读取实际 B6 HTTP 记录和私有封存快照，未将 0/49归因为程序不能运行。B6 有42个取得结果的题目、47个单资产/批次子调查，程序失败0。以下为逐题、多标签断点，**有重叠，不能相加**：

| 实际断点 | 涉及题数 | 定位层 |
|---|---:|---|
| 缺少适用或独立证据，事实存在但不能确认 | 30 | Evidence → Verification |
| 私有 Claim 有 range，公开投影将其丢失 | 26 | Artifact / Answer 投影 |
| 同范围来源冲突或范围分支适用性尚未解决 | 18 | Claim 作用域 → Verification |
| 明确修复约束没有转成可用修复值 | 8 | 来源字段 → Claim |
| 缺版本上下文 | 5 | Input / Context |
| 跨公告多资产输入超出现有单漏洞批次契约 | 2 | Input / API 范围 |

vLLM 是本轮确认的可修复断点：官方 `AFFECTS_VERSION: < 0.30.0` 已确认，原版本比较也已命中；但官方 `patched_versions: >= 0.30.0` 被当作单一版本解析，结果 `version=null`。等价修复事实又以不同 Claim ID 留存，核验整体保持 PENDING，原 Risk 因此合理地拒绝给出确定影响判断。

其他实际缺口没有被隐藏：5道事实题的 CWE、摘要缺少正式可核验输出契约；CVSS信息存在不足、未确认或投影缺口；PoC未发现状态未进入最终事实输出；风险/优先级策略与题目参考要求仍有差异。不存在将所有失败都归因于评分器的证据。

详细数量和样本见 `evaluation/reports/phase14b7-human49-20261016/baseline49-breakpoints.json`。

## 2. 真实修改

- 新增最小 `ImpactScope` 和原始来源绑定模型，复用现有 PyPI / PEP440 区间解析与比较。
- 仅在保存证据能证明来源字段 `/vulnerabilities/N/patched_versions` 明确为单一包含式修复下界时，规范化 `>= version`。不从受影响上界反推修复版，不支持的表达保留未知。
- 严格等价的同漏洞、同包、同作用域、同分支及同条件 Claim 可以规范化为一个事实，保留全部原始 Claim/Evidence ID 和原始值。
- 新快照在原有完整性检查后规范化，再封存。旧 Claim/Evidence 数据行和旧快照不更新。
- 非资产场景也保留已解析 OSV events，不再只留下不可比较的 JSON 文本候选。
- 新 Claim 的最终投影携带实际范围和证据绑定；旧答案保持旧投影。
- HTTP 适配校验读取同一正式答案投影；不直接比较原始 Claim 值与带证明元数据的答案值。**没有修改评测匹配公式、字段标准、分母或金标。**
- 平台/条件不同的范围不合并；未解决适用性不能确认。超过128个不连续区间的集合不截断成安全结论。

未修改 Planner Prompt、模型、Runtime执行逻辑、Risk规则、Gate规则、来源权威等级或补查预算。对应精确源文件哈希变更单独留痕，历史冻结配置保持原字节。

## 3. 8题真实 HTTP 定向验收

从B6正式结果选7题，另加按需求保留的缺版本预检控制。定向阶段将原先一个 PyTorch修复样本替换为 vLLM修复样本，以覆盖有足够官方证据的不受影响判断，原始初审记录仍保留。

| 场景 | 原结果 | 本轮结果 | 核心依据 |
|---|---|---|---|
| PyTorch漏洞事实 | PASS_WITH_WARNINGS，整题未匹配 | PASS_WITH_WARNINGS，仍有事实字段缺口 | 官方CVE身份不等于所有事实已核验 |
| PyTorch受影响版本 | UNKNOWN / REPLAN_REQUIRED | 继续 UNKNOWN / REPLAN_REQUIRED | 原来源尚不能形成全部适用已核验事实 |
| PyTorch多资产 | 两子调查UNKNOWN | 各自保留UNKNOWN | 资产及版本分别绑定，无相互污染 |
| vLLM 0.29.0 | UNKNOWN / REPLAN_REQUIRED | AFFECTED，MEDIUM，PASS_WITH_WARNINGS | 官方 `<0.30.0` 与明确修复下界 |
| vLLM 0.30.0 | UNKNOWN / REPLAN_REQUIRED | NOT_AFFECTED，LOW，PASS_WITH_WARNINGS | 同一官方范围的边界比较 |
| LangChain来源冲突 | HUMAN_REVIEW_REQUIRED | 保留冲突 / UNKNOWN | 不合并不同范围，不多数投票 |
| LangGraph证据不足 | REPLAN_REQUIRED | 保留UNKNOWN | 同一上游转载不变成独立官方确认 |
| 未提供版本 | NEED_CONTEXT | NEED_CONTEXT，无Planner/Run | 不生成缺失版本 |

共8题，7题进入完整调查链，包含8个单资产/批次子调查。2个确定影响判断及28条答案引用通过保存的 Claim/Evidence/RawDocument 绑定检查。旧47个原生调查绑定和47个封存核验快照哈希也通过兼容性检查，未再调模型重建旧答案。

这里的验收证明事实链与引用可追踪，**不是8题独立人工答案批准**。独立语义复核仍为PENDING。

## 4. 冻结环境及完整49题

- 代码：`17d43c39ab84d80cdda9334dc12997397a0f4cae`。
- 分支：`codex/phase14b7-impact-scope-closure`。
- Dataset：`AegisBench-v0.4-human49-20261014`，49条人工APPROVED；manifest SHA256：`002f021912a56f629c79a6207d30a91abe126c55f3d5f201adbfc358e8ae13e3`。
- Qwen：`aegisai-qwen25-planner:latest`，Ollama模型digest `15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16`；temperature 0，模型超时60秒，结构化JSON Schema。
- Planner：`investigation-plan-v6`，Prompt未改；答案使用确定性模板，本轮只增加已核验范围投影。
- 知识来源：原12份公共来源固定快照，原哈希不变；不是本轮实时采集。Embedding仍为原Mock384维，不能宣称全部模型组件都为真实模型。
- 独立新评测数据库；43个资产仅来自原问题明确输入，名称为中性随机值，不是企业扫描库存。
- 补查：原1轮/最多3次额外采集、原共享批次预算，未增加。
- Ground Truth仅用于最终比较，不进入Prompt、检索、Context或工具输入。
- `ONLINE_EVALUATION`：全部49题真实HTTP尝试；旧B6结果单独保留。

| 指标 | B6 | B7 |
|---|---:|---:|
| 题数 / 原严格分母 | 49 | 49 |
| 取得正式结果 | 42 | 42 |
| 缺上下文 | 5 | 5 |
| 范围不支持 | 2 | 2 |
| 程序失败 | 0 | 0 |
| 严格整题匹配 | 0/49 | **3/49** |
| 影响字段匹配，包含版本及风险题 | 0/27 | **4/27** |
| 风险等级匹配 | 0/10 | **1/10** |
| 优先级匹配 | 0/10 | **1/10** |
| 多资产优先结果匹配 | 0/6 | **1/6** |
| Patch状态匹配 | 1/10 | **2/10** |
| Gate PASS，按单/子调查 | 0 | 0 |
| Gate PASS_WITH_WARNINGS，按单/子调查 | 6 | **12** |
| Gate REPLAN_REQUIRED，按单/子调查 | 21 | **15** |
| Gate HUMAN_REVIEW_REQUIRED，按单/子调查 | 20 | **20** |

47个单资产/批次子调查，48次模型调用（包含原重试机制的一次额外尝试）、258次原始工具调用。补查新增采集调用0，新增Evidence0，新版答案v2为0。本轮改进来自对原有证据的规范化和传递，不能说是新增数据源的效果。

完整匹配题为 vLLM受影响版本、修复版本、多资产优先处理三题。数据只覆盖5个公告家族，相同问题类型高度相关，又参与过开发诊断；结果不能外推生产安全效果或泛化能力。

## 5. 仍然不能正确回答的原因

- 18个影响字段在新结果中仍有事实记录但未确认，主要涉及来源适用性、独立性及冲突。范围分支/部分范围与完整来源范围的语义尚未全面规范化，不能直接把它们合并。
- 5道事实题仍缺正式CWE和摘要事实输出；CVSS信息的证据/确认/投影缺口仍存在。
- 5道PoC题仍没有最终PoC状态输出。未找到有效证据不能改成已验证利用，也不能为了匹配而补NO_EVIDENCE。
- 8道风险题仍缺已确认事实；两道 vLLM 风险题已经判断影响，但完整风险答案仍不匹配：受影响场景的既有策略把已核验low严重性转换为MEDIUM，金标为LOW；不受影响场景输出优先级DEFER，金标为MONITOR。风险等级1/10和优先级1/10是两个字段指标，不能称风险整题匹配成功。
- 多公告多资产范围仍未支持，缺版本仍不启动调查；原评分因此保留未匹配，未将请求补充自动记成正确UNKNOWN。
- 20条来源定位未能解析，已明确列为 `LOCATOR_NOT_RESOLVED`；其余462条为按原JSON位置提取的片段。不能把片段存在当成语义支持。
- 补查没有获取到新的可消费来源，不能将补查框架存在当成实际证据覆盖改善。
- 此规范化目前作用于新核验快照与最终答案，未回写旧知识行或重建所有历史图视图。

下一处应定位的仍是**来源作用域/分支语义与缺少正式可核验事实的输出链**，不是增加Agent或继续包装演示。本阶段没有自动实施后续修复。

## 6. 指标界限与人工复核

严格整题匹配、风险等级和字段匹配均使用原评分器、原49题和原10道风险题。未知和不受影响没有做模糊匹配；失败/缺上下文/不支持都保留。

Evidence Coverage、Hallucination Rate、独立语义正确性均为 **PENDING_HUMAN**。42个取得结果的答案共323个输出Claim，需要原复核人员核对。49份复核表均未签字，不能用49题金标批准替代对本轮输出的审查。

Abstention Quality的既有结构化代理值为6/49（12.24%），其正确拒答计数仍为0、28题错误拒答、15题没有可评分判断、1个标识不一致。这是原规则的机械结果，不能宣称系统拒答能力已达标。版本指标的false_safe_count/false_affected_count均为0，仅适用于本轮适用样本；不等于系统安全率100%。

RAG-only和No Verification Agent两个对照均为NOT_IMPLEMENTED，没有编造提升幅度。

## 7. 实际测试

| 范围 | 实际结果 |
|---|---|
| 后端完整数据库回归，两个独立空测试实例 | **1751通过，0失败、0错误、0跳过、0排除；179警告，2052.15秒** |
| 本地便携后端 | 712通过，1个原入口排除，1警告；不能替代完整回归 |
| AegisBench | 138通过 |
| 前端 | 72通过，0失败、0跳过 |
| TypeScript / JS / HTTP /内部Schema导出 | 实际检查通过 |
| 旧结果兼容性 | 47个原生绑定、47个封存哈希通过 |
| 实现提交GitHub CI | 四项通过；最终交付提交另保存对应当前head CI回执 |

关键命令：

```text
python scripts/ci/run_database_tests.py --full --output work/phase14b7/full
python scripts/ci/run_backend_tests.py
python -m pytest tests/aegisbench -q
node --test tests/*.test.mjs
node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json
python scripts/ci/check_contracts.py
python scripts/export_investigation_api.py --check
python scripts/export_bench_http_schema.py --check
```

新增业务测试26项（25项单元断言和1项实际数据库/HTTP测试，后者覆盖两资产），均实际执行；1751是完整运行结果。中间失败全部留痕：新测试夹具尝试更新不可变Evidence而被拒，已改新增；HTTP适配器将带证明元数据的事实与旧原值直接比对，已改正式投影并校验旧47条；两项历史源哈希检查通过精确授权变更链更新，旧冻结文件未改；平台条件合并和过长区间集合的反例已修。没有改失败为跳过。

## 8. 修改文件与交付

业务范围：`backend/app/enrichment/impact_scope.py`、`agents/verification/impact_normalization.py`、`schemas.py`、`snapshot.py`、`investigation_api/projection.py`、`orchestration/composer.py`；HTTP适配校验 `evaluation/bench/http_investigation.py`。附加对应业务测试、历史哈希变更记录、CI测试入口和真实生成的契约。

- 机器结果、指标及49题事实链：`evaluation/reports/phase14b7-human49-20261016/`。
- 原始HTTP、完整本地日志及模型调用记录：本机 `work/phase14b7/`，私密配置不上传。
- 实际输出复核文件夹及ZIP：`outputs/AegisAI_Phase14B7_OutputReview_Package`，49题、12份原始来源、482个片段记录、49份未签表单及42份指标复核表。
- 关联草稿PR：[PR #32](https://github.com/shuabirfana-a11y/AegisAI/pull/32)，基于待合并PR #31。未合并、未发布、未自动进入下一阶段。

**最终回答：影响范围已经进入核验并影响风险/答案，但49题整体仍不能可靠作答；下一断点在剩余来源适用性和正式事实输出，而不是工程链路未启动。**
