# Phase 13-F.4：缺失上下文处理

在现有调查 HTTP 创建入口增加只读检查：原请求 → 既有 Scope/Normalizer → ContextCheck → 原 Planner。检查不访问外部资料、不调用模型、不写入资产，也不生成任务。

ContextResolution 状态：READY、LIMITED_INVESTIGATION、NEED_CONTEXT。版本影响需要漏洞、组件、版本；企业资产风险还需要用户提供的资产 ID。缺失的组件或版本保留未知。普通漏洞事实不要求部署信息；没有精确漏洞 ID 的公共资料搜索可进入 LIMITED_INVESTIGATION，仍由原 Planner/Runtime/Gate 处理。

要求来自冻结的实际问题目标与显式 profile，不能用 overview 标签隐藏风险/版本判断。原请求的版本来源证明必须与冻结 Scope 一致；公告修复版本、受影响范围、显式 null、UNKNOWN/空白不能成为部署版本。更宽的字面识别如果没有进入既有 Scope，需要用户补齐结构化字段，不能默认为 READY。纯隐式风险问题如“分析vLLM风险”也会请求上下文；公开事实搜索应明确使用 overview_v1。

## HTTP / 前端契约

仍使用 POST /api/investigations。新增 HTTP 200 的 ContextRequiredResponse；正常创建保持 202 和原响应。NEED_CONTEXT 是创建前的合法处理状态，**没有创建调查 ID、Planner/Agent/Gate 或 AnswerEnvelope**，不要轮询、不显示成风险安全或 Gate 通过。

以下 JSON 是合成协议示例，不是正式实验答案：

```json
{
  "status": "NEED_CONTEXT",
  "missing_fields": ["version"],
  "message": "请补充调查上下文；信息不足，不能判断资产影响或风险。",
  "next_actions": ["SUPPLY_CONTEXT", "PUBLIC_FACT_LOOKUP"],
  "investigation_created": false,
  "execution_mode": "NOT_STARTED"
}
```

status 是必填字面量。TypeScript 的 create() 返回 InvestigationCreateResult 联合类型；先根据 status 区分 NEED_CONTEXT 与正常创建，再读取 investigation_id。补全上下文时提交新请求/新幂等键，不覆盖旧调查。PUBLIC_FACT_LOOKUP 只是可选下一步：用户主动提交新的公开事实问题，不自动降低原风险调查目标。

NEED_CONTEXT 不占工作槽、不调用模型、不保留调查历史条目；前端保留自己的表单和补充记录。认证、已持久化幂等键和正在执行的同键请求冲突检查先于返回状态。相同拒绝请求可再次得到同样状态；服务关闭时仍返回原 503。

## 评测记录

HTTP 评测适配器保存原生 NEED_CONTEXT、missing_fields、NOT_STARTED，并返回既有 NOT_EVALUATED 状态、abstained=true。它没有可评分的影响/风险答案，不补 affected=UNKNOWN、risk_level=UNKNOWN，不伪造 AnswerEnvelope 或 REPLAN_REQUIRED Gate。

评分器、分母、Ground Truth、指标定义不修改。正式实验必须保留这些未评测记录，并用现有指标报告覆盖缺口；本阶段的“合法状态”不是“答案正确”或“模型调用成功”。

五题诊断只运行既定问题；上下文拦截与真实模型执行分别计数。是否具备后续实验技术准入依据实际保存结果，不运行 39 题。
