# Design System

产品是AI安全分析工作台。结构强调影响范围、来源时间、核验与修复，信息密度适中；六导航、七页面和跨页任务继承Phase 3。静态原型只是设计资产，不是生产工程。

## 颜色和状态

基础6色见VISUAL_DIRECTION，完整token见DESIGN_TOKENS。风险：严重critical、高危high、中危medium、低危low、未知info；核验：已确认success、待确认pending、证据不足warning、存在冲突conflict。失败error属于请求或任务，不与漏洞严重度混用。风险badge和字段核验badge并列显示，均带文字，不能用颜色单独作判断。

## Typography与Spacing

UI正文为Segoe UI/Microsoft YaHei UI，ID/版本/定位用等宽。页标题26、节标题17、正文14、表格13—14、次要12—13。4px基准允许2px微调，Default行密度优先，Compact减少padding。字体不依赖联网加载；正式前端按部署系统检验中文fallback，不承诺每台机器同字形。

## Radius、Borders、Shadow、Icons

4px短控件、6px容器、8px弹层，状态标签4px；不使用大圆角泡泡。一般区域仅1px边界，阴影只用于覆盖层。图标线性、19—20px、不承担无文案状态；窄屏导航仍有aria-label/title。没有机器人/星光/盾牌堆叠。

## Layout与Cards

216px左栏，64pxHeader，主区28px边距；1280变为200/22。标题与操作并排，说明一行，不设计Hero。总览四个metric；详情一个连续调查文档按章节分隔，右栏用于当前组件和章节锚点。Review/资产是队列与事实工作区；问答是结果+过程，不是气泡聊天复刻。

## Table规范

漏洞表六组：身份/产品、严重度、PoC/利用信号、修复、关键Claim核验、更新时间。长range/SHA放详情；来源/日期/未提供保持可读，不把多条评分平均。ID/标题可点击，行内Evidence入口独立。对齐左为文字，数值/日期按列统一；行hover不代表选择。稳定排序和分页同快照。窄屏仅表格容器横滚，整页不能横向溢出；保持身份列优先。

## Form与Feedback

Button primary每区域最多一个主要提交；read操作不套确认层。Input有可读label，必填/校验原因就地显示；native select作原型，生产组件可换但语义不变。Asset版本模糊先澄清，生产解析按生态规则，原型正则不是版本引擎。人工决定有预览/理由/确认，提交失败保留草稿。Toast用于轻反馈，关键错误留在区域内；未知不能只Toast后消失。

## Evidence、Conflict、Timeline

Claim上方，support/refute/context分列，Evidence卡含发布者/来源类型/原文/源与获取时间/URL/核验；技术定位折叠。镜像按lineage分组，不增加票。Conflict用低饱和局部横幅+两候选对照+原证据+Review入口，不卡住整页。Timeline每项必须有日期口径、来源、具体变化和证据；源日期缺失不由系统观察代填。

## Charts与Agent

总览只一个有明确问题的7天趋势；坐标、口径、范围、未知和数据日期必备。原型趋势明确非实测，没有Gauge/雷达/世界地图。Agent视觉区分问题范围、结构化结果、引用和公开工具摘要；事件必须来自真实任务后端才能显示运行成功，原型每块均标模拟，不展示隐藏Chain-of-Thought。

## 可实现性与适用边界

后续React/Vue可用成熟Table/Drawer/Modal/Form组件映射；本阶段不选框架，不建生产目录。外部内容用安全文本渲染而非可信HTML；状态依赖权限/coverage/as_of/revision。P1由capabilities门控；原型展示它们仅供评审，不宣布资产/复核已实施。

基本键盘：Tab/Enter、可见Focus、Ctrl/Cmd K、Esc关闭、弹层Focus trap和关闭后回原元素、跳至主要内容。文字配色和关键键盘路径已检查；读屏、完整Tab roving、全部可访问性及真实性验收在后续前端/联调继续，见UI_REVIEW。
