# Design Tokens

以prototype/styles.css的:root为原型实现值，tokens.json保存同值。Light Mode优先；Dark Mode不在本阶段实现，也没有无效主题按钮。

| Token | 值 | 用途 |
|---|---|---|
| --bg | #f5f7fa | 语义颜色/表面 |
| --surface | #fff | 语义颜色/表面 |
| --elevated | #fff | 语义颜色/表面 |
| --sidebar | #f0f3f7 | 语义颜色/表面 |
| --border | #d7dfe8 | 语义颜色/表面 |
| --text | #1e293b | 语义颜色/表面 |
| --secondary | #526173 | 语义颜色/表面 |
| --muted | #606f80 | 语义颜色/表面 |
| --primary | #0f766e | 语义颜色/表面 |
| --primary-hover | #0b615b | 语义颜色/表面 |
| --primary-soft | #e7f3ef | 语义颜色/表面 |
| --critical | #a42635 | 语义颜色/表面 |
| --critical-bg | #fcebed | 语义颜色/表面 |
| --high | #99501a | 语义颜色/表面 |
| --high-bg | #fff0e0 | 语义颜色/表面 |
| --medium | #805b12 | 语义颜色/表面 |
| --medium-bg | #fff6dd | 语义颜色/表面 |
| --low | #3c626e | 语义颜色/表面 |
| --low-bg | #edf4f6 | 语义颜色/表面 |
| --success | #23664b | 语义颜色/表面 |
| --success-bg | #eaf5ef | 语义颜色/表面 |
| --warning | #805b12 | 语义颜色/表面 |
| --warning-bg | #fff6dd | 语义颜色/表面 |
| --error | #a42635 | 语义颜色/表面 |
| --error-bg | #fcebed | 语义颜色/表面 |
| --pending | #526173 | 语义颜色/表面 |
| --pending-bg | #eef2f6 | 语义颜色/表面 |
| --conflict | #82445d | 语义颜色/表面 |
| --conflict-bg | #f7edf2 | 语义颜色/表面 |
| --info | #365e81 | 语义颜色/表面 |
| --info-bg | #eef4fb | 语义颜色/表面 |
| --font | "Segoe UI","Microsoft YaHei UI","Microsoft YaHei",sans-serif | 统一尺寸/层级/字体 |
| --mono | "Cascadia Code",Consolas,"Courier New",monospace | 统一尺寸/层级/字体 |
| --r-small | 4px | 统一尺寸/层级/字体 |
| --r-default | 6px | 统一尺寸/层级/字体 |
| --r-large | 8px | 统一尺寸/层级/字体 |
| --shadow | 0 8px 32px #1e293b1f | 统一尺寸/层级/字体 |
| --sidebar-width | 216px | 统一尺寸/层级/字体 |
| --z-header | 20 | 统一尺寸/层级/字体 |
| --z-backdrop | 40 | 统一尺寸/层级/字体 |
| --z-dialog | 50 | 统一尺寸/层级/字体 |
| --z-toast | 60 | 统一尺寸/层级/字体 |

## 尺寸与文字规范

基准4px，允许2px微调：4/6/8/10/12/14/16/18/20/22/24/28/32/40/48。Default优先，Compact只减少行/项padding，不缩小关键信息字号。页面内不另造色板。

| 角色 | 字号 / 行高 / 字重 | 用途 |
|---|---|---|
| Page Title | 26 / 1.3 / 650 | 中文页面任务 |
| Section Title | 17 / 1.4 / 650 | 阅读层级 |
| Card Title | 14 / 1.55 / 650 | 组件/事实标题 |
| Body | 14 / 1.55 / 400 | 原文解释、结果 |
| Table | 13—14 / 1.55 / 400 | Default；多行单元格优先于塞更多列 |
| Secondary | 13 / 1.55 / 400 | 日期、覆盖、范围 |
| Caption | 12—13 / 1.55 / 400 | 次要元信息 |
| Source/键提示 | 11—12 / 1.4 / 500 | 短标签；不能承载主要结论 |
| Code / ID | 13 / 1.55 / 400—600 | Cascadia Code/Consolas；原文定位可换行 |

图标19—20px、1.65px线宽。只有抽屉/弹层和Toast使用阴影，普通内容不浮起。layer：基础0、侧栏30、Header20、Backdrop40、Dialog50、Toast60、跳过内容80；页面已有positioning值以CSS为准。

表单控件36px，按钮small29—32px；交互主按钮padding8/12，正文页区padding18/20，页面边距28（1280缩为22）。Table简单行最小52px，复杂多行由内容自然到72—92px；不强制所有行高度，不能裁掉PoC/未知说明。

非交互结构边界浅色，输入边界更明确。Focus为2px主色外轮廓；hover用表面变化，不用发光或位移；disabled保留文案并不可操作。prefers-reduced-motion下不增加动画。
