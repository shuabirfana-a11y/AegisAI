## Phase 14-B1 PoC 富化（2026-10-14）

Artifact、证据/原核验链复用、只读查询与前端契约已完成。新增35项专项；相关186/186与 portable654项通过。真实库存读取2条候选，0条真实 VERIFIED_EXPLOIT；未执行利用或扫描。全量1574通过、2项既有 Unknown Context 失败保留。分支 codex/phase14b1-poc-enrichment，基于 Phase14A，尚未合并 main。完整结果见 PHASE_14B1_RESULT.md；停止在本阶段。

# AegisAI 当前阶段与待办

当前增量：2026-10-14，Phase 14-A 情报监测与富化补强已完成本阶段验收，见 [结果](PHASE_14A_RESULT.md)。分支 `codex/phase14a-monitoring-enrichment` 基于未合并PR #21，新增五个只读监测接口，原八调查接口不变。三类真实来源入库；本地Qwen规划→三专业Agent→Gate实跑为PASS_WITH_WARNINGS，论文经原语义问答可读。48项新增/相关验收合计70通过，便携CI641通过；完整回归的两项既有缺失上下文断言仍失败并记录，不能宣称全套全绿。来源网络失败、文献关联0、企业库存未提供均保持明确状态。Benchmark与人工答案未改变，未进行新一轮正式评测或部署。下面保留的是较早阶段快照，不代表当前阶段仍停在F.1。

更新日期：2026-10-13（北京时间）。ICT命题九AegisAI。Phase13-F.1已诊断原39题：35 Planner失败、2来源冲突导致Artifact不完整、2 UNKNOWN不匹配，原正式结果不回写。已修复单对象asset版本遗漏与明确目标overview错误触发资产分析；独立库仅实跑固定3题：事实PASS_WITH_WARNINGS、版本REPLAN_REQUIRED、风险QUERY_SCOPE_MISMATCH。115项评测测试通过；正式评测条件仍未全面恢复。没有改模型/Agent/Gate/金标/评分公式，未重跑39题。当前分支codex/phase13f1-evaluation-diagnostics，基于未合并草稿PR#16；依赖不自动合并。原输出的人审语义指标仍待复核。[本阶段报告](PHASE_13F1_RESULT.md)。

## 已有能力

- Model/Tool Gateway、混合检索、受约束 Planner、Runtime、三专业 Agent、Integration Gate、Investigation Orchestrator、AnswerEnvelope 已实现。
- Phase 12-B：8个调查 HTTP 接口、认证、CORS、脱敏响应、OpenAPI、TypeScript Client 和代理接线已实现；[前端对接文档](docs/PHASE12B_INVESTIGATION_API.md)。
- Phase 12-C：专用测试库的实际TCP完整链和未改动TypeScript Client八操作已验收；固定真实来源输入、模型模式隔离与当前交接文档已补齐。[本阶段结果](PHASE_12C_RESULT.md)。成功场景模型回执/数据仍为SYNTHETIC_TEST，不等于真实模型演示就绪。
- Phase 12-D：原生Windows Ollama/Qwen免费模型已安装，Gateway健康/文本/小型JSON实跑通过；用户已授权Planner输入Schema元数据补齐。最终默认模型两场景规划仍失败，实际HTTP没有三Agent/Gate成功结果。[本阶段未完成项](PHASE_12D_RESULT.md)。
- Phase 12-D.1：修复实际HTTP专用Planner的模型Schema及小范围输入/提示；原任务白名单、验证器、Runtime、Agent/Gate未改。最终Qwen2.5规划20/20，HTTP2/3 PASS_WITH_WARNINGS；Qwen3.5规划0/20，HTTP0/3。失败和原v2/v3对照全部留存。503可移植检查及60含数据库针对性检查通过，集合不相加；1项真实Embedding检查明确排除。
- Phase 12-D.2：初始五场景仅概览通过，组件-only仍FAILED，另三次Planner失败均保留；40秒诊断预算的资产/固定模板冲突复查均到Gate并被REPLAN_REQUIRED阻断。旧失败是资产缺口、单Artifact交接和未确认版本证据，不是格式错误。业务C类只报告，真实风险/冲突确定性闭环仍未验收。521项可移植检查和136项业务/诊断检查通过，集合重叠；四项SYNTHETIC规则控制不算真实调查。
- Phase 12-D.3：资产/版本/影响证据形成同一封存链；原核验、Risk、Gate规则不变。未知版本、缺证据、身份不明确及来源冲突保持阻断；旧数据无效证据不会自动修好。三个独立审查问题已最小修复；复现资料见 [固定演示说明](demo/phase12d3/README.md)。
- Phase13-D：原人工准入和 Metrics 复用，公开 Investigation HTTP 采集及 Offline 回放入口已准备；原生 Observation/Evidence/Risk 留痕，Mock 不能进入正式质量门禁。独立对照与语料/库存公平性仍待补齐。
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
| 人工标注与复核 | 用户复核包39通过/10退回已冻结，原Loader准入39；签署原件及退回均保留 | 修订10退回；未来实际输出另外做OutcomeAudit |
| 前端调查工作台 | 交接契约可用，队友页面进度待团队确认 | 队友按已开放HTTP联调；不直接调用内部Python服务 |
| 真实模型 | Phase12D.1推荐Qwen2.5：三类固定问题20/20合法规划、两次真实概览Gate通过；Qwen3.5不合格 | 使用本轮profile；范围仅固定问题，不代表事实/安全准确率 |
| 版本/资产闭环 | Phase12D.3 修复封存交接，指定演示资产及官方证据的最终真实 HTTP 场景 HIGH/P1、Gate PASS；无真实企业扫描库存 | 前端使用新可选字段；扩展真实资产数据前保留未知/阻断，不能推断全业务准确率 |
| 正式 AegisBench 实验 | 39题HTTP及离线评分已完成，严格整题匹配0/39；失败保留，Baseline未实现 | 等待实际输出独立复核及后续实验分析授权 |
| 比赛公网网址 | GitHub代码不等于网站已上线 | 团队确认部署方案后准备发布 |

## 验证记录入口

[Phase 12-B结果](PHASE_12B_RESULT.md)、[Phase 13-B结果](PHASE_13B_RESULT.md)、[Phase 13-C结果](PHASE_13C_RESULT.md)、[Phase 13-D准备进度](PHASE_13D_PROGRESS.md)。历史 1261/1288 项回归与本轮实际执行分开记录。

集成准备历史见 [集成准备记录](docs/INTEGRATION_PREPARATION_RESULT.md)。PR #6 的历史CI：[run 38144161139](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38144161139)；PR #7审查提交三项CI均通过：[run 38147011751](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38147011751)。Phase12-C的CI另按新PR提交记录，不借用历史结果。

原有8000/8769恢复及278条记录为Phase12C历史实测。Phase12D/12D.1使用临时本机TCP端口，结束后已关闭各自临时HTTP服务，不承诺8000/8769当前运行；模型服务11434保留。Phase12D.1两条成功链使用真实模型和已有真实来源，保留WAITING_REVIEW及未知风险，由原Gate允许有界概览；没有强迫确认安全结论。当前启动及配置见 [本轮说明](demo/phase12d1/README.md)。没有新增Agent、改Risk/Gate规则、填写人工答案或开发前端。
