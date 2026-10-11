# UX术语：所有页面共用

字段和Claim是核验单位，不能给整条漏洞一个无条件可信结论。内部enum可不同，但用户文案统一如下。

| 领域 | 用户文案/含义 | 禁用混淆 |
|---|---|---|
| 核验四态 | 已确认：明确scope内有可回查的确定性/人工依据；待确认：候选待检查；证据不足：不能确定且有缺口；存在冲突：同scope矛盾未解决 | 可信/高可信/Verified/模型自信98%替代四态 |
| 记录发布状态 | 已发布/已撤销/已拒绝/未知（published/withdrawn/rejected/unknown） | 发布状态不等于核验状态 |
| 影响三态 | 受影响affected / 不受影响not_affected / 无法判断unknown | unknown=安全；某漏洞不命中=系统无风险 |
| PoC关联 | 关联候选candidate / 已确认关联related / 未发现公开PoC（范围+截至）/搜集未完成 | 已关联=可用；未发现=确认不存在 |
| PoC可用性 | 未核验 / 已在授权环境验证（环境+记录）/在该范围失败/未知 | 所有环境可用；官方repo即测试成功 |
| 修复 | 明确修复版本fixed（包/分支/证据）/未获得明确修复版本证据 | last_affected下一版本即fixed |
| Patch | Patch关联候选 / 已确认关联（完整SHA/scope/Evidence）/未发现候选或未搜集 | 有commit=当前环境已修好 |
| 利用 | KEV已收录（目录/日期）；未在该次完整目录收录；未知；其他发布者利用评估单列 | 未收录=未被利用；PoC存在=真实利用 |
| EPSS | 利用概率预测、percentile、date/model_version | 官方综合风险指数；概率确定事件 |
| CVSS | 严重度，version/vector/source/scope完整 | 不同版本平均或天然矛盾 |
| 同步运行 | 正常/部分失败/失败/暂停；计划或未启用是配置状态；过期stale是时效状态 | 未启用=正常；lastchecked=lastsuccess |
| Review工作状态 | 待处理open / 已处理resolved / 暂缓deferred / 需重新复核reopened | 已处理不意味着结论必定已确认：可为证据不足 |
| 查询状态 | 排队/运行/完成/部分完成/失败/已取消（queued/running/completed/partial/failed/cancelled） | 动画播完=工具核验成功 |
| 知识类型 | 论文、研究分析、正式技术标准、指导框架、政策法规、风险知识/事件 | NIST指导框架=强制法律；风险分类=具体漏洞 |

## 时间与范围

published_at=源发布日期；modified_at=源修订；retrieved_at=系统取回；first_observed_at=首次观察；reviewed_at=核验；as_of=这次查询快照截止。网页Last-Modified/Git commit不代替发布时间。时间缺失显示“未提供日期”并保留原时间粒度，存储UTC/显示用户时区；仅日级原日期不伪装成精确到秒。

stale由来源/字段时效阈值与最后成功或分数日期确定；阈值来自调度配置，团队设置须显示，不是源SLA。旧数据仍可读，刷新不能把旧值当新获取。各种计数展示时间窗和coverage。

## null、空与缺失原因

null=未提供或未知；[]仅代表真实观测到的空集合。not_provided/unsupported/ambiguous/not_fetched/withdrawn分别显示未提供/尚不支持/存在歧义/尚未获取/源已撤销。Empty指没有初始记录，No Result指有效范围查询没有匹配，Error指未完成查询，三者不得统一“暂无数据”。

Evidence原文证据；Claim具体结论；Source采集入口；publisher实际发布者；lineage转录/镜像关系；RawDocument不可变原文版本；SyncRun一次实际同步任务。技术词首次显示中英/简短说明，定位/hash等放展开，不占主要用户阅读层。
