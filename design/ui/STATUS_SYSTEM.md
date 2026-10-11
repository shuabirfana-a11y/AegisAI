# Status System

继承UX_TERMINOLOGY，不替换业务语义。文字是主要状态信息，颜色是辅助；相同组件跨页同名同色。严重度与核验永远独立，允许“严重 + 证据不足”。

| 轴 | 状态 / 用户文案 | 视觉 |
|---|---|---|
| 严重度 | Critical严重 / High高危 / Medium中危 / Low低危 / Unknown未知 | critical/high/medium/low/info；带CVSS版本/来源 |
| Claim核验 | 已确认 / 待确认 / 证据不足 / 存在冲突 | success / pending / warning / conflict；按字段scope |
| PoC关联 | 已确认关联 / 发现PoC候选 / 未发现公开PoC / 搜集未完成 | info / pending / neutral / pending；显示已查范围与截至 |
| PoC可用性 | 未核验 / 已在授权环境验证 / 范围内失败 / 未知 | pending / success+scope / warning+scope / neutral |
| PoC争议 | 证据不足 / 存在争议 | 用相应Claim四态，不创造“可靠PoC”总开关 |
| Patch | 关联候选 / 已确认关联 / 未发现 / 未获取 | pending / info / neutral / pending；SHA/branch与Evidence |
| 资产 | 受影响 / 不受该漏洞影响 / 无法判断 | high / success+scope / warning；只针对明确对象 |
| 来源运行 | 正常 / 部分失败 / 失败 / 暂停 | success / warning / error / pending |
| 来源配置 | 计划 / 未启用 | pending；不能绿色正常；研究probe不计成功 |
| 时间 | 数据过期 / as_of / 源日期未知 | 局部warning/date说明，不覆盖整页旧事实 |
| Review工作状态 | 待处理 / 已处理 / 暂缓 / 需重新复核 | pending/success/pending/warning；不等于事实已确认 |
| Agent任务 | 排队/运行/完成/部分完成/失败/取消 | info/pending/success/warning/error/pending；源自事件 |

## 页面状态

七页均有Loading、Empty、Error、Partial和Stale的可切换高保真变体，截图保存在screenshots/。另外原型可看Conflict、Evidence Insufficient、Source Offline、No Result、Permission；Agent Timeout仅问答可选。不能用加载Skeleton当0记录；Empty初始空与No Result查询无匹配的恢复按钮不同。

Partial/Stale/Offline保留已有事实、原范围和日期，用局部横幅说明缺口。Error保留条件和request ID；人工写超时先查幂等结果，409保留草稿；403不诱导重试。状态例来自模拟数据，不代表实际API成功/故障注入。

原型左下“原型检查”是评审控制，正式产品不包含。真实业务仅消费后端status/coverage/revision，不接受这个选择器改变最终情报。
