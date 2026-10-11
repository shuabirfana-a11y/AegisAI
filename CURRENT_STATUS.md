# AegisAI 当前阶段与待办

更新日期：2026-10-11（北京时间）。项目为 ICT 命题九、奇安信 AI 安全知识情报系统。PR #6、#7 已经负责人确认并合入 main，当前稳定基线为 `8e0bfe6bd398d26fc7270e5f0b5aeb6d03d354fd`。本轮 Phase 12-C 在 `feature/phase12c-http-integration` 完成联调准备，通过 [PR #8](https://github.com/shuabirfana-a11y/AegisAI/pull/8) 交付，独立复查通过，尚未合入 main；不涉及 SentinelGraph 或恒脑。

## 已有能力

- Model/Tool Gateway、混合检索、受约束 Planner、Runtime、三专业 Agent、Integration Gate、Investigation Orchestrator、AnswerEnvelope 已实现。
- Phase 12-B：8个调查 HTTP 接口、认证、CORS、脱敏响应、OpenAPI、TypeScript Client 和代理接线已实现；[前端对接文档](docs/PHASE12B_INVESTIGATION_API.md)。
- Phase 12-C：专用测试库的实际TCP完整链和未改动TypeScript Client八操作已验收；固定真实来源输入、模型模式隔离与当前交接文档已补齐。[本阶段结果](PHASE_12C_RESULT.md)。成功场景模型回执/数据仍为SYNTHETIC_TEST，不等于真实模型演示就绪。
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
| 人工标注与复核 | 仓库登记的人工完成和APPROVED均为0，任务材料已备；成员的新进度尚未收到 | 收取实际答案和证据，登记真实标注/复核人，逐题签核 |
| 前端调查工作台 | 交接契约可用，队友页面进度待团队确认 | 队友按已开放HTTP联调；不直接调用内部Python服务 |
| 真实模型 | 默认Mock没有PlannerPlan；固定torch真实来源场景实际HTTP得到PLANNING_FAILED；受控合成TCP完整链通过 | 配置规划模型并在真实数据上重新验收；不把Mock、旧确定性Assistant或配置Schema检查冒充真实模型效果 |
| 正式 AegisBench 实验 | 没有已批准标准答案，不能发布正式准确率 | Ground Truth达到准入后再授权实验 |
| 比赛公网网址 | GitHub代码不等于网站已上线 | 团队确认部署方案后准备发布 |

## 验证记录入口

[Phase 12-B结果](PHASE_12B_RESULT.md)、[Phase 13-B结果](PHASE_13B_RESULT.md)、[Phase 13-C结果](PHASE_13C_RESULT.md)、[Phase 13-D准备进度](PHASE_13D_PROGRESS.md)。历史 1261/1288 项回归与本轮实际执行分开记录。

集成准备历史见 [集成准备记录](docs/INTEGRATION_PREPARATION_RESULT.md)。PR #6 的历史CI：[run 38144161139](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38144161139)；PR #7审查提交三项CI均通过：[run 38147011751](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38147011751)。Phase12-C的CI另按新PR提交记录，不借用历史结果。

本机 API 8000、代理 8769、开发库 55436 已恢复，现有漏洞列表返回 278 条记录。旧确定性 Assistant 实测 COMPLETED / PASS_WITH_WARNINGS；新调查的成功闭环仅在专用测试库的显式合成场景中验证。启动与联调方法见 [演示检查](docs/BACKEND_DEMO_STABILITY.md)，本轮验证见 [稳定性结果](docs/BACKEND_INTEGRATION_STABILITY_RESULT.md)。没有新增 Agent、改风险/Gate 规则、填写人工答案或开发前端。
