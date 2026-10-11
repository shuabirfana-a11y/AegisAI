# Evidence视觉系统

“结论→支持/反驳/上下文→原文与出处”是视觉主线。一个Claim可对应多个Evidence，但重复转载按lineage聚合，不用来源数量作可信百分比。

## Claim与证据卡

主文的Claim行给字段/value、scope、四态、来源日期和“查看依据”。抽屉590px，上方固定Claim header：身份/范围/当前revision/状态；正文来源卡；底部返回原字段及P1Review入口。移动/Tablet不超过屏宽，原页面保留origin和位置。

Evidence Card：来源名称与来源类型→支持哪个Claim及support/refute/context→原文片段→published/modified/retrieved（各自标签）→原始URL→核验状态。locator/raw ID/hash/lineage在details展开，不占主阅读层。原文quote以浅底和左侧细规则识别，不用大引用图标或知识图谱。

示例中mock://链接及mock-hash明确不可当真实证据；当前模糊或不完整源字段不填造日期。生产必须显示实际publisher/provider而非只有采集平台ID；原文许可受限时显示允许片段和官方链接，不做全文下载承诺。

## 多来源与历史

同源转录卡列“同源上下文”，独立支持/反驳有文字关系。CVE/OSV同一GHSA不能绘成三票确认。源scope不同先说明；同scope矛盾局部Conflict Banner，保留两原文并跳对应Review。不同CVSS版本并列，不能仅因为分值不同染成冲突。

点击Citation或字段入口打开同一抽屉；Esc/关闭返回触发元素，Tab不跑到背景；直接证据深链接未来应带对象面包屑，旧raw revision引用持续可读。新revision提示可比较，不静默替换历史引用。

Loading仅证据区Skeleton；一张卡失败不删其他卡；SourceOffline读已有带日期raw；证据不足说明not_fetched/unsupported/ambiguous等原因；无权或许可受限不泄露全文。BACKEND REQUIRED E01—E04/A08/A09：Claim、provenance、原文定位、关系与权限，当前都未实现。
