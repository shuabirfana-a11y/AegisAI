# 页面状态与恢复规则

状态可以叠加：某源离线导致字段过期/部分缺失，不能因此清掉所有详情。未知不是错误，冲突只作用于对应scope。后续UI需为下表适用状态出稿；NA不生成无意义面板。

| 状态 | 总览 | 中心 | 详情 | 资产 | 待复核 | 问答 | 系统运行 |
|---|---|---|---|---|---|---|---|
| Loading | 保留窗口/旧统计 | 保留条件/游标 | 身份/旧快照先读 | 保留选中组件/草稿 | 保留任务/草稿 | 真queued/running | 保留source过滤 |
| Empty | 尚无运行情报 | 该类型尚无记录 | 无当前记录看历史 | 未登记→添加 | 无开放问题 | 尚无调查→推荐 | 尚无run/未启用 |
| Error | request ID/重试 | 重试同条件 | 单区重试/回原入口 | 读失败/登记失败分开 | 读写恢复分开 | query ID/已证实部分 | 读失败/重试任务分开 |
| Partial Data | 标缺源模块 | 已查/未查范围 | 缺字段保留其他事实 | 未完匹配+unknown | 某证据失败仍对照 | 已完成工具/缺口 | partial run范围/失败集合 |
| Stale Data | 日期/last success | 来源及范围日期 | 每字段日期/旧证据 | 情报+库存revision | 提交须最新revision | 回答引用日期/缺口 | last success不被失败覆盖 |
| Conflict | 具体对象入口P1 | 关键Claim标记P1 | 并列同scope+复核P1 | 匹配依据分歧P1 | 对照候选/人工决定 | 引用并列/建议复核 | 处理记录冲突链接；非运维错误 |
| Evidence Insufficient | 关注项注明不足 | 候选/未知筛选 | 字段unknown+原因 | 无法判断/补版本 | 留unknown/补证理由 | 限制结论/恰当拒答 | 记录缺证链接；非run成功判据 |
| Source Offline | 异常→source | 旧结果/未查范围 | 旧Evidence可读 | 旧匹配/时效提示 | 旧候选仍能读 | 哪个工具/结论受影响 | 故障run/退避/恢复状态 |
| Agent Timeout | NA（本页无任务） | NA | 去现有问答任务，无本页Agent | 去现有问答任务 | NA | query ID/partial/取消或显式重试 | NA（Sync timeout另属run失败） |
| No Result | 当前窗口无匹配 | 调整/清除筛选 | 关联区未匹配并标范围 | 未匹配≠全部安全 | 过滤无任务 | 已查询但无匹配/扩大范围 | 当前source/status无run |
| Permission | 私有/P1动作门控 | 私有资产筛选门控 | 公共事实与私有子区分开 | 无权对象不披露 | 无write只读证据 | 拒绝越权工具范围 | 无retry权限不可发任务 |

## 恢复优先级

1. 展示已获得且允许读取的事实；未完成区不显示0或“没有”。保留过滤、origin、滚动、版本和用户草稿。
2. Error重试实际失败读取；Partial Data只重试缺口，写操作先查幂等结果；403不诱导重复点击；409对照新revision后重新人工提交。
3. Empty提供启动所需的真实配置入口；未实现能力只说明未接入/隐藏入口，不提供假按钮。No Result显示已查范围、时间口径及调整条件。
4. Source Offline/Stale Data保留旧证据及时间；不能把历史值当当前结论。Conflict进入对应Evidence/Review，Evidence Insufficient保留unknown/补信息。
5. 超时/取消问答不损失已核验结果；有用的partial必须标出未完成部分。所有回答都仍可回到Evidence。

## 反馈协议（BACKEND REQUIRED）

响应需request_id、status/reason、as_of/revision、coverage、partial failures、字段unknown reason；不得输出secret或私有原文。写操作需服务端actor/权限、expected_revision或幂等key、实际接受/排队/落地状态。字段null/[]语义继承Phase 2，404历史对象/撤销与403访问限制要明确处理。

点击刷新可能改变快照，界面提示变化，不静默重排已读结果。确认对话只用于有后果的人工写决定/登记、离开未保存草稿；查询不增加层层“AI分析确认”。

状态验收是设计走查：11状态×7页均已逐项标适用或NA；真实交互速度/键盘可用性/读屏/错误注入在后续前端与联调实测，当前不宣称已通过用户测试。
