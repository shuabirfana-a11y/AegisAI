# 七页高保真说明与前端交接

沿用Phase 3任务、导航与优先级，不重做业务结构。原型全部7页可运行；以下是组件和数据设计输入，不是正式API/数据库。截图以1440/1280为主。

## 情报总览 [DASH]

原型路由：`#/overview`；对应Phase 3元素：D01—D07。

**结构**：四指标→重点列表→趋势/演示组件→来源摘要→知识入口。

**主要动作**：本期示例集合/严重度/PoC入口进入相应筛选；异常转Source/run。

**视觉判断规则**：首屏的风险依据与源时效需可见，避免只看数字。

**状态**：Loading/Empty/Error/Partial/Stale均有可切换原型和截图；相关Conflict/缺证/离线/No Result/Permission见STATUS_SYSTEM，AgentTimeout只问答。

**数据与分期**：业务值全部BACKEND REQUIRED；P1资产/Review/Patch不能凭原型当已实现。读取需coverage/as_of/revision/unknown reason和Evidence；写操作需权限/actor/幂等及并发。

## 情报中心 [CENTER]

原型路由：`#/center`；对应Phase 3元素：C01—C06/K01。

**结构**：五类型Tab→本页搜索/基础筛选→高级→六组表格→分页。

**主要动作**：搜索、产品/严重度/四态/PoC/KEV/fixed/date筛选和排序；知识详情。

**视觉判断规则**：长range和所有评分不挤在行里，未知桶不隐藏。

**状态**：Loading/Empty/Error/Partial/Stale均有可切换原型和截图；相关Conflict/缺证/离线/No Result/Permission见STATUS_SYSTEM，AgentTimeout只问答。

**数据与分期**：业务值全部BACKEND REQUIRED；P1资产/Review/Patch不能凭原型当已实现。读取需coverage/as_of/revision/unknown reason和Evidence；写操作需权限/actor/幂等及并发。

## 漏洞详情 [DETAIL]

原型路由：`#/detail/CVE-XXXX-A001`；对应Phase 3元素：V01—V12/E01—E04。

**结构**：身份→影响→风险→处置→Evidence/冲突→关联→时间线。

**主要动作**：就近证据抽屉、同scope复核、上下文问答、回原调查。

**视觉判断规则**：核心页：范围与明确fixed优先，核验与严重度独立；连续文章层级。

**状态**：Loading/Empty/Error/Partial/Stale均有可切换原型和截图；相关Conflict/缺证/离线/No Result/Permission见STATUS_SYSTEM，AgentTimeout只问答。

**数据与分期**：业务值全部BACKEND REQUIRED；P1资产/Review/Patch不能凭原型当已实现。读取需coverage/as_of/revision/unknown reason和Evidence；写操作需权限/actor/幂等及并发。

## 资产风险 [ASSET]

原型路由：`#/assets`；对应Phase 3元素：S01—S05。

**结构**：演示组件队列→三态判断→原因→相关漏洞→处置/问答。

**主要动作**：精确版本登记；原型新输入保持unknown；查看版本依据。

**视觉判断规则**：P1，默认不查公网、不建CMDB；不受某漏洞影响不等于安全。

**状态**：Loading/Empty/Error/Partial/Stale均有可切换原型和截图；相关Conflict/缺证/离线/No Result/Permission见STATUS_SYSTEM，AgentTimeout只问答。

**数据与分期**：业务值全部BACKEND REQUIRED；P1资产/Review/Patch不能凭原型当已实现。读取需coverage/as_of/revision/unknown reason和Evidence；写操作需权限/actor/幂等及并发。

## 待复核 [REVIEW]

原型路由：`#/reviews`；对应Phase 3元素：R01—R05。

**结构**：问题队列→Claim/scope→两候选Evidence→人工决定/理由→预览→审计。

**主要动作**：内存模拟值/actor/理由审计、409草稿说明、返回Claim。

**视觉判断规则**：P1，同scope真实冲突与缺证区别，原观察保留。

**状态**：Loading/Empty/Error/Partial/Stale均有可切换原型和截图；相关Conflict/缺证/离线/No Result/Permission见STATUS_SYSTEM，AgentTimeout只问答。

**数据与分期**：业务值全部BACKEND REQUIRED；P1资产/Review/Patch不能凭原型当已实现。读取需coverage/as_of/revision/unknown reason和Evidence；写操作需权限/actor/幂等及并发。

## 智能问答 [QA]

原型路由：`#/assistant`；对应Phase 3元素：Q01—Q07。

**结构**：可见问题范围→结构化发现/引用→工具摘要→续问输入。

**主要动作**：运行固定模拟查询、取消/超时状态、引用回Evidence/对象。

**视觉判断规则**：真实实现不得播放伪工具动画或展示私有CoT；P1资产受权限限制。

**状态**：Loading/Empty/Error/Partial/Stale均有可切换原型和截图；相关Conflict/缺证/离线/No Result/Permission见STATUS_SYSTEM，AgentTimeout只问答。

**数据与分期**：业务值全部BACKEND REQUIRED；P1资产/Review/Patch不能凭原型当已实现。读取需coverage/as_of/revision/unknown reason和Evidence；写操作需权限/actor/幂等及并发。

## 系统运行 [SYSTEM]

原型路由：`#/system`；对应Phase 3元素：Y01—Y05。

**结构**：来源表→run历史→失败详情→基础健康NA。

**主要动作**：失败/计划过滤、run详情、模拟queued重试、来源说明。

**视觉判断规则**：last_success不被失败覆盖，计划源不绿色；本原型没有实际健康监控。

**状态**：Loading/Empty/Error/Partial/Stale均有可切换原型和截图；相关Conflict/缺证/离线/No Result/Permission见STATUS_SYSTEM，AgentTimeout只问答。

**数据与分期**：业务值全部BACKEND REQUIRED；P1资产/Review/Patch不能凭原型当已实现。读取需coverage/as_of/revision/unknown reason和Evidence；写操作需权限/actor/幂等及并发。

## 共用导航、状态及交接

全局搜索Ctrl/Cmd K按公开ID/产品/知识/授权资产；本页过滤互不替代。后续真实服务只加载允许scope，不开放自由SQL、任意URL、PoC执行或用户越权写。原型没有API调用或token。

正式前端建议按Shell/Search/Status/Table/Evidence/Review/AgentResult等组件拆分，JS原型只供版面与行为参考；不把mock-data或原型正则直接当业务事实/版本匹配引擎。API适配与错误处理根据Phase 3 24项提案复核；本阶段不定React/Vue品牌、状态管理库或Dify接入。

组件展示读取结构化实体/Claim，并将源字段映射成View Model，未知不能统一空字符串。风险排序可解释，查询快照不静默重排；旧证据引用绑定版本。返回保留filters/cursor/scroll/origin/query上下文，HTTP路径由后续架构落实，不是本原型hash路由。

原型覆盖主要点击、输入、筛选、分页、Drawer/Modal、固定查询与内存审计。完整Multi Select/任意日期弹层、生产capabilities/auth、长列表虚拟化、并发提交/恢复和真实Agent生命周期仅定义契约，尚未实现。正式开发优先检验详情与Evidence数据可落地，然后中心/总览/系统/问答，再P1工作区。

所有mock条目可替换：is_mock标识、CVE-XXXX-…、mock://原文、mock hash及固定query trace不能进入生产事实。部署时显式移除评审状态选择器与模拟按钮；先真实接入再开放P1，禁止靠网页mock数字声称多源运行或Benchmark已达标。
