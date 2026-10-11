# UI参考调研

2026-10-03，仅学习信息组织方法，不复制页面、品牌、商业权限体系或源代码。以下采用原则是本项目的设计推论；来源是产品官方文档，不是声称我们获得其私有控制台权限或逐像素检查截图。

| 产品 / 官方参考 | 观察到的信息方法 | 不适合AegisAI的部分 | 采用原则 |
|---|---|---|---|
| [GitHub Security overview filters](https://docs.github.com/en/code-security/reference/security-at-scale/overview-dashboard-filters) | 按严重度、生态包及启用范围缩小视图，说明访问范围；不同条件可组合 | 完整组织/企业权限与大量仓库配置会扩大本项目范围 | 筛选语义可见，类型/生态与来源覆盖明确；权限不由职业推定 |
| [Datadog Table Widget](https://docs.datadoghq.com/dashboards/widgets/table/) | 表格比较分组值、排序、上下文链接及N/A表达 | 高度自定义Dashboard和广泛监控指标不适合首期 | 缺失为未知，不填0；计数能进入同条件列表；任务就近展开 |
| [Linear Search](https://linear.app/docs/search) | 全局检索与当前视图检索区分，可按ID/对象类型检索并调整过滤 | 不采用任务项目管理结构、收藏体系或其品牌样式 | 全局搜索是共享入口，本页筛选独立；键盘进入但不增加导航项 |

Snyk旧Reports入口本轮打开已返回Page Not Found，不将旧索引内容当现行界面证据；OpenCTI、CrowdStrike、Wiz、Defender、Grafana本轮未作直接界面验证，不编造观察。三项已核实参考足够支撑筛选、表格、上下文导航原则，原型依然以Phase 3流程为主。

设计自选浅色中性背景、低饱和青绿操作、少量结构容器；没有复制参考产品颜色/商标/布局。Evidence与同scope冲突由本项目冻结Claim/lineage要求推导，不借参考产品的分数或资产覆盖背书。

文字对比度阈值按[W3C Contrast Minimum说明](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)：普通文字至少4.5:1；本轮核对主要配色组合，同时用文字/状态名称避免仅靠颜色。未进行全面读屏与全部WCAG条目审计，不宣称认证。
