# Phase 12-D.3 资产风险联调变化

仍使用原有八个调查接口。本阶段没有新增 URL，也没有修改前端页面。

## 提交资产调查

在 `/api/investigations` 的 `asset_scope` 中提交已注册、当前用户拥有的 `asset_id`、精确 `component_id`，以及选择组件的 `component`（name / ecosystem / package_name / version）。字段以 `investigation-http.openapi.json` 为准。资产列表、组件资料仍由现有资产 API 获取。

原始问题、精确版本和库存不一致时继续阻断。只有组件字符串不能证明某台企业资产，缺少资产身份不自动建资产。当前规划仍根据原始受约束输入工作：组件版本未随请求提供时可能要求补充，不能让模型在计划中猜测库存版本。

## 读取

`GET /api/investigations/{id}/artifacts` 的 `verification` 增加两个可选数组：

- `version_observations`：固定库存版本快照。含资产名称、发行包、版本、环境、暴露、库存修订、观察时间、来源 Artifact、回执追溯和 `is_demo`。
- `impact_version_evidence`：原有影响/修复 Claim 对应的来源证据。`status` 是这条证据的关联状态；只有其自身是核验支持/冲突证据时才承接 Claim 状态。某条 Claim 被确认不等于所有候选证据都被确认。

风险结果和 `AnswerEnvelope` 继续读取已有接口。最终答案从封存 Gate 上下文读取，不重新调用模型。历史响应可能没有上述数组，前端按空数组处理，不把缺失解释为安全。

## 展示约束

`OWNER_INVENTORY_NOT_SCANNED` 表示用户库存，不是扫描证明；`is_demo=true` 必须显示演示库存。`criticality` 目前保持 `unknown`，没有新增重要性评分规则。

`NOT_AFFECTED` / LOW 只针对本次所选组件与漏洞。版本缺失、范围未解析、来源不足时仍 UNKNOWN；冲突仍保留 CONFLICT / HUMAN_REVIEW_REQUIRED，不能在客户端换成绿色通过。

官方来源适用条件、实际端口暴露、功能启用、补丁是否应用仍需单独调查。本次 CVE-2025-47277 场景未扫描 PyNcclPipe/跨节点通信端口，不表示成功利用已验证。

## 契约

已同步 HTTP OpenAPI / TypeScript 和内部 Schema / TypeScript；`api/reference` 与 `contracts/generated` 镜像同步。内部 `VerificationRequest.supporting_artifacts` 由服务器构建，浏览器不能传入这些引用授予权限。
