# 本地 Model Provider 实测记录

日期：2026-10-12。状态：**PARTIAL / 不具备稳定真实调查演示条件**。这是调用协议、规划兼容性和 HTTP 接线检查，不是 AegisBench，不报告安全准确率。

## 运行条件

Windows原生 Ollama v0.40.3；RTX5060 Laptop 8GB，内存约15.2GiB。运行时 zip 来自官方发布，验证 SHA-256 `e5ecff02dfc7cae8ddf6d6b7a7ac5f727ffeedf4491f44ae75ff5b0820dbbbd5`。本地监听11434，云能力关闭，没有配置收费模型 Key。

默认模型 `qwen2.5:7b-instruct-q4_K_M`，项目别名 `aegisai-qwen25-planner:latest`；16K上下文，4096输出上限，`json_schema`。模型摘要 `15aaf3fda3b8e9bb6724e5e9911eec3b9cbdb6bd967646b6bf49ee9846b7ec16`。曾观察到 Ollama 报告100% GPU、约5.5GB驻留；这是当时的运行状态，不保证其他时刻驻留。Embedding 仍为 Mock，未运行 embedding 推理。

原生初始化首次冷启动有60秒 TIMEOUT，预热后调用成功。另下载 Qwen3.5 4B 做一次模型兼容替代检查，无收费服务、业务框架或业务规则变更。[Qwen3.5来源](https://ollama.com/library/qwen3.5:4b)。

## 最终默认配置实跑

时间：`2026-10-12T04:44:02.173103Z`。实际命令：`python backend/scripts/probe_model_provider.py --mode REAL --output work/phase12d/provider-report.final-profile.json`，本机已加载 `local-real-profile.json`。

| 检查 | 结果 |
|---|---|
| 健康 / 文本生成 | 通过 / 通过 |
| 小型JSON结构检查 | 5次尝试，5次符合Schema |
| 纯CVE规划 | 2次尝试，PLANNING_FAILED / FALSE_MISSING_INPUT |
| torch2.5.1影响/补丁规划 | 2次尝试，PLANNING_FAILED / FALSE_MISSING_INPUT |
| 11条Gateway调用回执 | 11条协议层成功；不能等同于合法规划 |
| 延迟 | 最短314.83ms，最长6682.29ms，平均2587.75ms，包含健康检查 |
| Token | 10条有统计，合计22053；健康调用统计为null |
| 探测器ready | false，退出码1 |

小型JSON问题使用明确的合成CVE/risk/evidence形状，仅判断结构是否合法，不验证回答值是否正确。5/5不是业务准确率或总体JSON稳定性结论。Planner仍使用 `task-plan-v1` 和原白名单、权限、覆盖、DAG验证；模型自报confidence不当作安全可信度。

## 兼容尝试与限制

保留每次实跑的失败记录，没有把非法计划补字段后重新计为成功。Qwen2.5 的 `json_schema`、`json_object` 和独立temperature=0配置未获得本轮两场景验收；Qwen3.5冷加载超时，默认思考输出在64token文本检查中截断，配置 `MODEL_REASONING_EFFORT=none` 后健康/文本/小型JSON可用。

Qwen3.5 的服务端 `json_schema` 两场景仍拒绝；`json_object` 出现任务工具白名单及Provider失败。现有 `prompt_json` 模式有一轮小型JSON5/5、Planner1/2（纯CVE合法，复杂查询INVALID_JSON），另一个temperature=0配置未通过。**孤立一次合法计划不能证明可靠性，当前不推荐把这些配置用于比赛现场。**

私有失败候选和所有中间报告保留在本机忽略目录，公开摘要不包含原始模型输出、提示词、服务地址、密钥或个人资产。代表性的脱敏调用回执见 [provider-calls.json](phase12d/provider-calls.json)。

## 最终真实HTTP检查

固定已有真实来源 CVE-2025-32434 / torch2.5.1，经临时Uvicorn实际本机TCP进入原 Investigation API与Orchestrator；模型使用最终默认配置，不是TestClient、MockTransport或预生成Artifact。

结果见 [http-check.json](phase12d/http-check.json)：创建202；状态、Trace、Artifact、Answer、History、Cancel均返回200；Integration返回409 RESULT_UNAVAILABLE。Planner失败，0个专业Agent、0份Artifact、无Gate；AnswerEnvelope状态FAILED。持久化模型身份为REAL / PERSISTED_PLANNER_CALL。两次读取失败答案一致且没有额外模型调用；完整成功答案冻结性质由受控合成TCP回归另行验证。

AnswerComposer保持既有确定性模板。没有实现LLM答案重写，没有让模型决定核验、风险或Gate状态；独立 `generate_text()` 通过只证明文本接口能力。

## 工程检查和下一步

实际测试命令、批量失败及复测详见 [PHASE_12D_RESULT](../PHASE_12D_RESULT.md)。实际模型调用与受控HTTP协议测试分别标注，绝不借用合成链声称真实链成功。

下一步仍需在单独授权范围内解决模型与Planner的规划兼容性，并重新验收真实HTTP链。当前没有改Planner提示词、验证规则、Runtime、专业Agent、Risk/Gate规则或Evaluation Runner，没有正式评测和公网部署。
