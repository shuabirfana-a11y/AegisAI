# 全局导航与上下文

## 打开与搜索

默认总览，展示上次选择的公开时间窗和覆盖范围。已经有深链接时直达可访问对象；会话过期后恢复目标而不是返回空首页。没有要求建设专门登录/用户管理系统，仅消费现有最小会话权限[G01]。

全局搜索[G02]出现在七页顶部：CVE/GHSA/OSV ID精确优先；产品/包显示生态和规范身份，别名歧义返回候选；知识按标题/外部ID/版次返回；资产仅检索当前授权范围。分组结果“漏洞/产品/知识/资产”，显示范围与过期提示。产品结果进入情报中心带产品筛选，资产进入资产页，知识进入共享知识详情。未接资产能力不出现资产结果组。空查询不自动抓外站。

## 路由与返回

| 当前操作 | 目标 | 必须携带/保留 |
|---|---|---|
| 总览新增/风险卡 | 中心的相同集合 | type/window/coverage/as_of/filter/sort；计数和列表同快照 |
| 中心漏洞行 | 详情 | entityID/revision、origin与列表filters/cursor/scroll |
| 中心知识行 | 共享知识详情 | type/ID/edition、origin与列表位置 |
| 详情某字段“查看证据” | Evidence抽屉 | ClaimID/scope/raw revision/anchor |
| Evidence“进入复核”[P1] | 对应Review任务 | reviewID/ClaimID/当前revision；关闭或提交回原字段 |
| 详情“继续询问这个漏洞” | 唯一问答工作区 | entityID/revision/当前Claim，可编辑问题chip |
| 资产“分析为什么影响我”[P1] | 同一问答工作区 | 授权assetID/inventory revision/entityID，不自动带主机名到公共服务 |
| 问答引用/结果 | 证据或详情 | queryID、result offset、scope/as_of/revision，返回后保留回答 |
| 总览异常源 | 系统来源及失败任务 | sourceID和异常status；默认最近失败run |
| 系统run行 | SyncRun子视图 | runID、source filters/cursor；关闭回同源任务列表 |

全部路由是UX提案，尚未实现。详情不是一级菜单；面包屑“情报中心→CVE…”并提供“返回调查结果”避免从问答回错误入口。详情内章节锚点不增加一级菜单。

## 统一上下文[G03/G05]

URL仅包含公开type/entity/revision/anchor及公开筛选。assetID和敏感query不直接写可公开分享URL，使用受权限约束的会话上下文引用；私有页面分享后仍检查授权。origin使用内部已知路由key，不接任意跳转网址。

返回恢复筛选、页游标、滚动、打开的Claim和as_of。后台有新revision只显示“有新版本”；用户主动刷新后更新快照并说明变化，不能静默重排正在阅读的结果。Evidence旧版保留原引用，允许切最新并比较。对象被withdrawn/rejected仍可查看历史状态，不当不存在。

## Agent入口与权限

一个专用工作区，顶部导航可进入；上下文按钮是快捷跳转，不能叠加全局悬浮聊天窗。没有上下文时展示推荐问题；有上下文时展示可移除chip、原调查返回按钮。先由工具读事实再生成回答；当前问题不赋予资产、复核或采集权限。

资产登记、Review决定、Sync retry分别由Asset write/Review write/运维retry授权；服务器仍需复核权限。无权读私有资产显示“无法访问该对象”，不透露它的存在/版本；公共证据可读时继续开放。无权写可看公开候选依据，但不显示可执行提交控件。

统一状态恢复[G04]：加载保留原查询；失败仅重试该读取；写入未知结果先凭request/idempotency_key查状态，不能盲目再提交；404/撤销区别处理；403不给“重试能解决”提示。
