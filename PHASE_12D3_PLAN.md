# Phase 12-D.3 资产风险业务闭环修复计划

> 实施方式：按用户本轮正式实施授权，在已附加的 AegisAI 工作树内执行；使用 executing-plans 的逐项测试流程及一次最终独立审查。

基线：`1537ffdc36a52e6d5aaec876534d70cec5d62d43`，分支 `codex/phase12d3-asset-risk-loop`。

目标：让资产库存版本与影响范围证据进入原有核验、风险和 Gate 链路。保持模型、任务白名单、Runtime、核验规则、风险计算及 Gate 标准。

## 已定位原因

- 核验只纳入选定漏洞任务的祖先回执，遗漏独立/后续的资产、版本、证据任务。
- 版本比较输出是观察，缺少正式可追溯的版本 Observation。
- 部分来源范围被投影为只有 raw_expression 的候选，丢失已提供的结构化版本信息。
- 风险输入只含资产 ID，库存读取时间与原调查时间不一致；无资产 ID 的组件描述不能证明企业资产。
- 存量 PyTorch 案例还有不合格证据，补齐资产不能把这些证据自动变成 CONFIRMED。

## 执行任务

### 1. 资产、版本领域对象及完整回执交接

涉及 `backend/app/agents/asset_observations.py`（新增）、verification schemas/snapshot、orchestration handoff。

- [ ] 先写失败测试：分开的 get_asset / inspect_component_version 回执必须进入核验，跨运行/失败/错误目标引用拒绝。
- [ ] 定义 frozen VersionObservation 与 ImpactVersionEvidence；记录源 Artifact、回执、时间、哈希与库存修订；未知字段保留未知。
- [ ] 新增有界、精确的 supplemental Artifact 引用；原始 Investigation Artifact 不变；核验仍处理所有原有 Claim。
- [ ] 空扩展字段不参与历史序列化，验证已有审计哈希兼容。

### 2. 原有核验和风险的输入适配

涉及 verification snapshot、tooling verification、analysis snapshot/schemas。

- [ ] 先写失败测试：影响证据与版本 Observation 关联、库存修改后仍读取调查快照、身份/所有权不匹配拒绝。
- [ ] 影响范围只来自原始结构化来源/原有 Claim 与 Evidence，复用版本解析；不猜版本、修复版本或确认状态。
- [ ] 风险消费核验封存的版本快照，增加资产名称与追溯信息；规则不变。
- [ ] 验证 unknown、缺证据、组件不匹配、冲突保持原有谨慎语义；如发现已有输出协议自相矛盾，只做一致性适配并独立记录。

### 3. 验证和交付

- [ ] 五类固定场景测试；使用测试库，合成证据明确标识，不能算 Ground Truth。
- [ ] 至少一次本地 Qwen 真实 HTTP 资产风险调查。仅使用可追溯官方数据，演示库存明确 is_demo；不声称扫描了企业。
- [ ] 全量后端回归，检查 OpenAPI/TypeScript 契约，同步必要导出。
- [ ] 精确源文件变更许可记录；核验、Risk 与 Gate 规则文件哈希不变。
- [ ] 一次独立代码审查，修复实质问题，写 PHASE_12D3_RESULT.md。停止本阶段。

## 审查重点

1. 引用另一个用户/运行的资产回执不能获得事实授权。
2. 有旧版本或失败工具时，不能用新库存填补观察或丢弃冲突。
3. 同一组件多个版本/包别名歧义，必须保留 UNKNOWN。
4. 影响证据与观察必须绑定同一漏洞、发行包和来源，不能仅凭引用地址确认。
5. 历史上下文序列化及 Artifact 哈希不能因新增默认字段失效。

## 范围说明

没有真实扫描资产材料时，用明确标记的演示库存验证真实来源业务链；模型真实调用与资产真实性分别报告。源证据仍不合格则继续阻断，不为验收删除 Claim。
