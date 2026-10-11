# AegisAI 离线UI原型

七个核心页的高保真设计资产，全部数据与执行反馈均为模拟；不是正式前端，没有后端/API/数据库/Dify/模型/Collector。P1资产/复核只供设计评审。模拟ID为CVE-XXXX-…，mock://链接不通向真实出处。

## 打开

可直接用浏览器打开本目录index.html，地址默认#/overview。也可以在工作区根目录用Python静态文件服务：

```powershell
& 'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m http.server 8768 --bind 127.0.0.1 --directory prototype
```

然后访问http://127.0.0.1:8768/。本轮已使用Codex捆绑Python启动；服务只绑定本机。纯静态文件，不安装依赖。若端口被占用可选择另一端口；文件直接打开仍能查看全部页面。

## 操作

左栏六导航，漏洞详情从中心/问答进入；Ctrl/Cmd K全局搜索，Esc关闭抽屉；中心过滤/排序/分页，Evidence在原上下文展开；Review填理由、预览后才模拟提交；新增演示组件的影响保持unknown。所有原型写操作仅内存，刷新恢复。

桌面左下“原型检查”切Loading/Empty/Error/Partial/Stale等状态与Default/Compact密度。AgentTimeout仅问答。P1模块不代表生产能力。固定问答结果不会调用模型，所有tool trace和SyncRun都标模拟；重试仅改变示例queued状态。

Design System/状态/组件/响应式/前端数据映射见../design/ui/。screenshots/、browser_validation.json、visual_review.json是内部QA；不作Benchmark或生产性能证明。下一阶段接真实服务时需按Phase 3契约替换Mock、校验权限并移除评审控制器，不能复制原型版本正则当业务逻辑。
