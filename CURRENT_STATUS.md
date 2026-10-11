# AegisAI 当前阶段与待办

更新日期：2026-10-11（北京时间）。项目为 ICT 命题九、奇安信 AI 安全知识情报系统。本文件对应集成准备分支，main 发布状态需要单独确认；不涉及 SentinelGraph 或恒脑。

## 已有能力

- Model/Tool Gateway、混合检索、受约束 Planner、Runtime、三专业 Agent、Integration Gate、Investigation Orchestrator、AnswerEnvelope 已实现。
- Phase 12-B：8个调查 HTTP 接口、认证、CORS、脱敏响应、OpenAPI、TypeScript Client 和代理接线已实现；[前端对接文档](docs/PHASE12B_INVESTIGATION_API.md)。
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
| main 集成 | 原PR #2、#3、#4、#5 的成果已汇到 `chore/aegisai-integration` 候选；尚未进入main | 通过集成PR统一审查，负责人确认后合并；不覆盖队友工作 |
| 人工标注与复核 | 仓库登记的人工完成和APPROVED均为0，任务材料已备；成员的新进度尚未收到 | 收取实际答案和证据，登记真实标注/复核人，逐题签核 |
| 前端调查工作台 | 交接契约可用，队友页面进度待团队确认 | 队友按已开放HTTP联调；不直接调用内部Python服务 |
| 真实模型 | 默认 Mock，真实供应商尚未配置 | 由团队选定服务，在后端环境配置；不把Mock冒充真实调用 |
| 正式 AegisBench 实验 | 没有已批准标准答案，不能发布正式准确率 | Ground Truth达到准入后再授权实验 |
| 比赛公网网址 | GitHub代码不等于网站已上线 | 团队确认部署方案后准备发布 |

## 验证记录入口

[Phase 12-B结果](PHASE_12B_RESULT.md)、[Phase 13-B结果](PHASE_13B_RESULT.md)、[Phase 13-C结果](PHASE_13C_RESULT.md)、[Phase 13-D准备进度](PHASE_13D_PROGRESS.md)。历史1288项回归与本次集成检查分开记录。

本轮本地检查和来源一致性见 [集成准备记录](docs/INTEGRATION_PREPARATION_RESULT.md)。GitHub检查是否通过，以集成PR当前提交的Checks为准。

本轮只处理已有成果的集成与工程检查；没有新增Agent、改风险/Gate规则、填写人工答案或开发前端。
