# AegisAI 当前阶段与待办

更新日期：2026-10-12（北京时间）。项目为 ICT 命题九、奇安信 AI 安全知识情报系统。PR #6、#7 已经负责人确认并合入 main，稳定基线为 `8e0bfe6bd398d26fc7270e5f0b5aeb6d03d354fd`。Phase12C的 [PR #8](https://github.com/shuabirfana-a11y/AegisAI/pull/8) 和Phase12D的 [PR #9](https://github.com/shuabirfana-a11y/AegisAI/pull/9) 尚未合入main。本轮 `codex/phase12d1-planner-stability` 在其上完成 **Phase12D.1：Qwen2.5固定问题20/20合法规划，两次真实HTTP三Agent/Gate/Answer有界概览验收**。Qwen3.5不合格、版本/资产场景Gate失败，未声称全业务真实验收。详情：[本轮结果](PHASE_12D1_RESULT.md)。

## 已有能力

- Model/Tool Gateway、混合检索、受约束 Planner、Runtime、三专业 Agent、Integration Gate、Investigation Orchestrator、AnswerEnvelope 已实现。
- Phase 12-B：8个调查 HTTP 接口、认证、CORS、脱敏响应、OpenAPI、TypeScript Client 和代理接线已实现；[前端对接文档](docs/PHASE12B_INVESTIGATION_API.md)。
- Phase 12-C：专用测试库的实际TCP完整链和未改动TypeScript Client八操作已验收；固定真实来源输入、模型模式隔离与当前交接文档已补齐。[本阶段结果](PHASE_12C_RESULT.md)。成功场景模型回执/数据仍为SYNTHETIC_TEST，不等于真实模型演示就绪。
- Phase 12-D：原生Windows Ollama/Qwen免费模型已安装，Gateway健康/文本/小型JSON实跑通过；用户已授权Planner输入Schema元数据补齐。最终默认模型两场景规划仍失败，实际HTTP没有三Agent/Gate成功结果。[本阶段未完成项](PHASE_12D_RESULT.md)。
- Phase 12-D.1：修复实际HTTP专用Planner的模型Schema及小范围输入/提示；原任务白名单、验证器、Runtime、Agent/Gate未改。最终Qwen2.5规划20/20，HTTP2/3 PASS_WITH_WARNINGS；Qwen3.5规划0/20，HTTP0/3。失败和原v2/v3对照全部留存。503可移植检查及60含数据库针对性检查通过，集合不相加；1项真实Embedding检查明确排除。
- GitHub 私有仓库、分支、CI与前端交接包已有；三项 CI必须按当前提交验证，不能把历史结果挪用。
- AegisBench 框架及49题候选已有；人工标注规范、独立复核流程和10/20/19分批材料已有。

## 24题与49题

| 版本 | 问题文件 | 数量 | 用途 |
|---|---|---:|---|
| AegisBench-v0.1 | evaluation/datasets/AegisBench-v0.1/questions.jsonl | 24 | 保留的早期候选 |
| AegisBench-v0.2.1-pilot | 复用 evaluation/datasets/AegisBench-v0.2-pilot/questions.jsonl | 49 | 当前人工标注候选 |

新版问题文件 SHA-256：f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1。

新版包含49个不同 ID，事实5、版本17、POC/Patch10、风险10、多跳7；只覆盖5个公告簇，不能称作49个独立漏洞。原题 [questions.jsonl](evaluation/datasets/AegisBench-v0.2-pilot/questions.jsonl) 与 [分类目录](evaluation/ground_truth/QUESTION_CLASSIFICATION.md)互相对应。

旧版已填写的人审材料保留并注明版本，不能按行号直接搬入新版。机器参考答案仍为待人审资料；只有真正独立人审的记录才能进入正式 Ground Truth。

## 尚未完成

| 待办 | 当前事实 | 下一动作 |
|---|---|---|
| 本地启动稳定性 | PR #7修复已经合入main；使用实际PostgreSQL运行状态与有限超时，不再误信失效PID标记 | 继续使用现有启动脚本；新机器需配置本机运行环境 |
| 人工标注与复核 | 收到外部zip的49条HUMAN_RECORD/DRAFT、121条证据，结构/摘要检查通过；尚未独立复核或导入，仓库APPROVED仍0 | 由不同成员逐题查源复核；不把结构检查当人工批准 |
| 前端调查工作台 | 交接契约可用，队友页面进度待团队确认 | 队友按已开放HTTP联调；不直接调用内部Python服务 |
| 真实模型 | Phase12D.1推荐Qwen2.5：三类固定问题20/20合法规划、两次真实概览Gate通过；Qwen3.5不合格 | 使用本轮profile；范围仅固定问题，不代表事实/安全准确率 |
| 版本/资产闭环 | 推荐模型计划合法，但实际Gate FAILED，缺资产Scope及版本/包Scope匹配、复核等待 | 下一次授权定位交接与证据原因，保持原Gate拒绝，不强制通过 |
| 正式 AegisBench 实验 | 没有已批准标准答案，不能发布正式准确率 | Ground Truth达到准入后再授权实验 |
| 比赛公网网址 | GitHub代码不等于网站已上线 | 团队确认部署方案后准备发布 |

## 验证记录入口

[Phase 12-B结果](PHASE_12B_RESULT.md)、[Phase 13-B结果](PHASE_13B_RESULT.md)、[Phase 13-C结果](PHASE_13C_RESULT.md)、[Phase 13-D准备进度](PHASE_13D_PROGRESS.md)。历史 1261/1288 项回归与本轮实际执行分开记录。

集成准备历史见 [集成准备记录](docs/INTEGRATION_PREPARATION_RESULT.md)。PR #6 的历史CI：[run 38144161139](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38144161139)；PR #7审查提交三项CI均通过：[run 38147011751](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38147011751)。Phase12-C的CI另按新PR提交记录，不借用历史结果。

原有8000/8769恢复及278条记录为Phase12C历史实测。Phase12D/12D.1使用临时本机TCP端口，结束后已关闭各自临时HTTP服务，不承诺8000/8769当前运行；模型服务11434保留。Phase12D.1两条成功链使用真实模型和已有真实来源，保留WAITING_REVIEW及未知风险，由原Gate允许有界概览；没有强迫确认安全结论。当前启动及配置见 [本轮说明](demo/phase12d1/README.md)。没有新增Agent、改Risk/Gate规则、填写人工答案或开发前端。
