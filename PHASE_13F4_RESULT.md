# AegisAI Phase 13-F.4：未知上下文处理结果

**已完成本阶段，状态 CONTEXT_HANDLING_READY。** 同样 5 题都有合法处理结果：4 题完成真实调查调用，未知版本题返回 NEED_CONTEXT，不再发生 Planner 失败。达到本阶段允许“完整调查或明确请求上下文”的技术准入门槛；没有运行 39 题、计算准确率或改变评分标准。

## 1. 原因与处理边界

F.3 未知题的第一次模型输出使用 `<version>` 占位调用；重试又漏掉原 Validation 必须的补充版本任务。它在 Planner 失败，没有到达 Gate。F.4 采用创建前的上下文检查，明确请求用户补充信息，避免把不完整请求继续交给模型猜测。

只修改 HTTP Adapter/契约和评测 HTTP 传输适配。原 Normalizer、Scope、Planner/Prompt、Validation、Runtime、专业 Agent、Risk、Gate、Evaluator/指标和人工答案均保持原字节。本轮 574 个受保护文件摘要一致，详见 docs/phase13f4/PROTECTED_HASHES.json。

## 2. 缺失信息设计

链路：原请求 → 既有 Normalizer/冻结 Scope → ContextCheck → 原 Planner；需要补充时停止在合法的 preflight 状态。

| 场景 | 必要信息 | 处理 |
|---|---|---|
| 精确漏洞事实 | 已提供目标 | READY；不要求资产或部署版本 |
| 公共资料发现 | 问题的查询范围 | LIMITED_INVESTIGATION；仍走原 Planner/Gate |
| 版本影响 | 漏洞、组件、版本 | 缺失则 NEED_CONTEXT；不自动创建资产 |
| 企业资产风险 | 漏洞、组件、版本、资产 | 缺失则 NEED_CONTEXT |

需求根据冻结的实际目标和显式 profile 判断，不能用 overview 标签隐藏风险/版本请求。UNKNOWN、空白、显式 null、公告修复版本、影响范围不能当部署版本；原始信息来源必须证明已捕获 Scope。字面信息若没有进入旧 Scope，也请求补齐结构化字段，不让 Planner 面对不一致的上下文。

没有新增安全判断：版本未知不表示安全，没有把 REPLAN_REQUIRED 改成 PASS，也没有让模型生成风险或核验结论。补全后由用户提交新请求；PUBLIC_FACT_LOOKUP 是用户可主动选择的新公开事实调查，不自动降级原风险目标。

## 3. 状态流转与 API

仍使用 POST /api/investigations，已有正常创建为 HTTP 202。新增 HTTP 200 ContextRequiredResponse：status=NEED_CONTEXT、missing_fields、message、next_actions、investigation_created=false、execution_mode=NOT_STARTED。

NEED_CONTEXT 是创建前状态，不是新调查阶段，也不是 Gate 结果。没有调查 ID、Planner Run、Agent Artifact、Integration Result 或 AnswerEnvelope；不占工作槽，不调用模型。前端显示补充字段，不轮询状态接口。

完整请求继续原状态流：PLANNING → INVESTIGATING → VERIFYING → ANALYZING → INTEGRATING → AnswerEnvelope。Gate 的原有阻断保持。

认证、已有历史幂等键以及正在执行的同键 fingerprint 冲突检查先于缺失响应；服务关闭仍为 503。被拦截的新请求没有调查历史条目，前端保存自己的表单；补全上下文提交新幂等键，不覆盖旧结果。

## 4. 五题实际结果

执行日期：2026-10-14；开始时间 08:40（北京时间）。原 39 条 APPROVED 数据中使用同样 5 条，问题、Gold、评分和模型/提示均未改变。请求使用新隔离来源副本及 4 个中性受控演示资产，不是企业扫描数据。

| 原题 / 场景 | HTTP | Planner | Gate / 上下文 | 交付 |
|---|---:|---|---|---|
| GHSA-53q9-r3pm-6pq6-facts / 漏洞事实 | 202 | VALIDATED | PASS_WITH_WARNINGS | COMPLETE_WITH_WARNINGS |
| GHSA-935w-9g4m-p28p-affected / 版本影响 | 202 | VALIDATED | REPLAN_REQUIRED | INCOMPLETE |
| GHSA-53q9-r3pm-6pq6-risk-affected / 资产风险 | 202 | VALIDATED | REPLAN_REQUIRED | INCOMPLETE |
| GHSA-c67j-w6g6-q2cm-affected / 来源冲突 | 202 | VALIDATED | HUMAN_REVIEW_REQUIRED | REVIEW_REQUIRED |
| GHSA-53q9-r3pm-6pq6-unknown / 版本未知 | 200 | NOT_STARTED | NEED_CONTEXT，missing_fields=[version] | 提示补充；无风险答案 |

实际为 **5 次 HTTP 提交、4 个调查、4 次原模型调用**。最后一题不是“完整链路成功”，而是合法请求补充；不能把 5 个合法状态写成 5 个完成的调查。

原 Qwen2.5 / aegisai-qwen25-planner:latest，温度 0、timeout 40 秒、max_output_tokens 4096、json_object、提示 investigation-plan-v6。模型 manifest digest 与 F.3 一致；没有下载、换模型或调整提示。原 Embedding Mock 配置沿用，真实执行标签只基于已保存 Planner 调用。

实际模型用量：input_tokens 25593、output_tokens 2607、total_tokens 28200；模型调用耗时合计约 71.73 秒。这是调用统计，不是准确率或泛化指标。

## 5. Trace 与原始记录

4 个真实调查都保存了 Planner、Runtime、Investigation/Verification/Risk Artifact、Integration 和 Answer；部分核验/风险仍未确认，Gate 阻断原样保留。

| 场景 | Investigation ID | Integration ID |
|---|---|---|
| 事实 | ceda74b6-2d04-46a8-b616-9d4c41b2c74b | 4bd52214-c5dd-4dcf-a2bc-a7827983f92f |
| 版本 | 554c9b12-b340-4119-a494-cdeca5720dd6 | 62b9094b-ddf1-4d04-b2f5-993e1c7aab83 |
| 风险 | e0e918bb-8ecb-45c6-8ce4-2f387179dbc7 | 46cffcd3-4e6d-4ec0-b0c3-2098a480392d |
| 冲突 | ac9dfd40-9946-4c7a-96a0-aef74da82ab8 | 8fb8c079-0222-4f2e-8332-2b247806adf1 |
| 未知 | 未创建 | 未创建 |

原始请求/响应、逐次模型文本、Artifact 引用和 Runtime 审计在 evaluation/failure_analysis/phase13f4/diagnostic5。summary.json 区分 FULL_CHAIN 与 NEED_CONTEXT；未知题保存原生补充信息响应，不伪造 Trace。

## 6. Benchmark 与 39 题准入

已恢复本阶段五题的**合法输入处理技术门槛**，可进入下一阶段授权的 39 题实验；这不证明其他 34 题全部可规划，也不证明业务答案正确。

未知题在评测适配器里保存 NEED_CONTEXT、缺失字段、abstained=true，使用现有 NOT_EVALUATED 状态。没有补 affected=UNKNOWN 或 risk_level=UNKNOWN，没有伪造 AnswerEnvelope。原评分器仍把没有可评分答案的样本视为不可用，不给正确答案分、不改分母、不删除样本。未来实验必须披露这种覆盖缺口。

本次正式 39 题执行为 0，新增准确率/幻觉率为未评测；正式运行等待下一阶段指令。原 Ground Truth 39 APPROVED / 49 候选保持不变。

## 7. 测试与复审

本次本地只运行相关检查：**103 passed**，1 个既有 AnyIO 弃用 warning。其中新增后端 29 个、评测传输适配器 1 个控制；不把新增数量与重叠回归相加。缺版本、缺资产、缺漏洞、信息完整、overview 语义、公告/null 版本、冻结 Scope、并发幂等和前端判别字段均覆盖。

独立只读复审验证 30 个新控制通过，已报告问题全部修复；没有在复审中调用模型/API。HTTP 10 个导出文件、评测 11 个 Schema 组与实际代码一致，42 个 HTTP 操作保持原数量，TypeScript 检查退出码 0。

未重新运行全量本地后端套件；历史 1426/1261 项验收不冒充本次结果。具体命令见 docs/phase13f4/TEST_EVIDENCE.md。离线执行 `python evaluation/failure_analysis/phase13f4/summarize.py` 可复现处理统计，不调模型/API/评分器。

## 8. 修改范围与前端影响

新增 context_check.py、控制测试；更新 investigation_api service/schemas、调查创建路由、HTTP 评测适配器、TypeScript create 返回联合类型、两个契约导出、CI 的新控制清单及本阶段文档/诊断记录。

前端类型/API 客户端和现有交接包 reference 已同步，create() 返回 InvestigationCreateResult。队友需要先检查 status===NEED_CONTEXT，再决定显示补充输入或读取 investigation_id；不修改前端 UI。公开响应没有 API Key、数据库配置或模型 Token。

基线 33f62a46d4c57423f79fc034449bf3f93171fc53（PR #19）；冻结实现 525e6bf7d648160c6b6b7eec97ba787aa891661c；分支 codex/phase13f4-missing-context。独立工作树延续 AegisAI，未切换项目或合并 main。

## 9. 停止与当前限制

完成上下文管理和限定 5 题验证后停止。没有修改 Gold/Gate/评分、运行 39 题、增加 Agent 或优化模型。

NEED_CONTEXT 的补充由用户主动提交，不提供自动补全或旧调查恢复；其历史条目不存在。当前仍有版本/风险证据不足和来源冲突，需要保持 REPLAN_REQUIRED/HUMAN_REVIEW_REQUIRED。词法识别范围有限，结构化上下文仍是更可靠的输入形式。

该检查接入 HTTP 调查入口；直接调用旧 Python Planner 服务不会自动经过它，旧服务的缺失字段校验保留。这不等于修改或修好了模型自己的补充信息任务生成。
