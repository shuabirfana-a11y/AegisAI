# Phase12-D.2 真实场景扩展与失败分析执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. 本任务已获用户直接执行授权，按以下步骤持续执行；不等待额外计划确认。

**Goal:** 定位原版本/资产调查的真实阻断原因，固定扩展五类场景，交付可追溯失败案例及分析报告。

**Architecture:** 复用已有真实HTTP探测、持久化Planner审计和原Agent/Gate读接口。新代码仅用于本阶段测量与脱敏诊断；不改变业务决策。

**Tech Stack:** 当前Python/FastAPI/Pydantic/PostgreSQL，本机既有Qwen2.5和Model Gateway。

**Spec:** 本轮用户“Phase12-D.2：真实场景扩展验证与失败模式分析”指令；历史证据为docs/phase12d1/http-chain-receipts.json。

## Global Constraints

- 不调Prompt，不新增或更换模型，不修改Runtime、Agent、Risk、Gate、Task/Tool白名单或Evaluation Runner。
- 类型A Schema缺失、类型B接口适配只在证据证明且回归测试覆盖后允许最小修复；类型C业务问题只报告，保留阻断。
- 五类：漏洞概览、组件版本、资产风险、证据不足、来源冲突；输入固定且记录来源。
- 不伪造资产或官方证据。真实库存/冲突不足时使用独立测试库明确标识的合成控制，不计为真实业务验收。
- 每条记录关联原始调查/Planner/Artifact/Gate ID；只导出脱敏数据，不导出Token、环境配置或原始模型响应。
- 不进行正式Benchmark、准确率评价、公网部署或自动合并main。

## Review Focus

- 缺资产与组件-only输入必须保持区别，UNKNOWN不视为NOT_AFFECTED。
- 工具执行成功与证据支持结论分别记录，不能用HTTP200或JSON合法替代Gate验收。
- 原数据库没有某类数据时，不能以合成控制声称真实来源验证。
- 中断、无Gate结果及来源不足必须保留原状态，不假造REPLAN/HUMAN状态。
- 公开诊断只读已有数据及本阶段审计；公开元数据走现有脱敏函数。

### Task 1: 定位历史失败并检查数据基础

**Files:** 创建evaluation/failure_cases/历史案例及docs/phase12d2/诊断回执；私有临时诊断放忽略目录work/phase12d2。
**Consumes:** InvestigationOrchestrator.store.read_audit、PlannerTraceStore.read、三个Agent Reader、IntegrationReader以及只读库存查询。
**Produces:** 明确的scope→plan→artifact→Gate映射、规则源码位置和A/B/C/数据缺口分类。

- [ ] 读取既有失败调查06cc6ede-6437-487b-a7d0-c9fd3410a4ca，核对真实模型、任务、工具、版本输出及原Scope。
- [ ] 读取库存、Claim/Evidence/Conflict可用性；比较两个历史概览成功案例，不修改其记录。
- [ ] 将每个阻断逐条关联Artifact与需要补充的信息，保存脱敏诊断。
- [ ] 核对JSON、引用ID、数据来源及UNKNOWN；提交Task1产物。

### Task 2: 固定场景HTTP扩展与控制验证

**Files:** 创建demo/phase12d2/cases.json、backend/scripts/probe_investigation_failures.py和针对性诊断测试；复用既有探测，不改生产模块。
**Consumes:** run_stability_case、owned_http_client、ModelGateway既有profile、Task1数据发现。
**Produces:** 五类实际执行回执，分别标注真实来源、用户库存或合成控制，失败阶段/Gate规则/缺失信息清单。

- [ ] 新诊断逻辑先用合成数据验证缺Gate、未知版本、来源冲突、脱敏和类型分类，先观察失败后实现最小工具。
- [ ] 建立固定输入，单次串行真实模型HTTP调用，必要的合成场景在独立测试库隔离且明确标识。
- [ ] 保留所有成功与失败，没有结果也记录；不为通过率修业务。
- [ ] 运行新增测试及相关现有回归，提交Task2。

### Task 3: 报告、核验与交付

**Files:** 创建PHASE_12D2_RESULT.md、docs/phase12d2/验证记录；更新CURRENT_STATUS.md；生成本机文件夹/ZIP。
**Consumes:** Task1/2真实回执及新增测试输出。
**Produces:** 用户指定八项报告、最小修复/业务问题分类、GitHub草稿PR及可发送文件夹。

- [ ] 运行当前后端可移植基线、相关Agent/Gate回归、契约与安全检查，区分历史与本次结果。
- [ ] 一次完整分支独立审查，必要修复限制于诊断工具，业务问题保持报告。
- [ ] 保存最终失败案例、报告与说明；沿既有授权发布草稿PR，验证当前提交CI，不合并main。
- [ ] 打包并检查文件哈希和敏感信息，完成后停止。
