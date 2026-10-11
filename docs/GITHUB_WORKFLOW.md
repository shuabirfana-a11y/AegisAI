# GitHub 协作流程

仓库：[shuabirfana-a11y/AegisAI](https://github.com/shuabirfana-a11y/AegisAI)，保持 private。当前 main 已包含 Phase 11-D、Phase 12-B 调查 HTTP API，以及前端交接和 AegisBench/49 题材料；发布状态见 [CURRENT_STATUS](../CURRENT_STATUS.md)。

## 稳定基线

注释标签 **v1.0-phase11D** 绑定最初上传的提交 **d5bf67321fa9641d01260234c0f3c9691fed2ca3**。以后工程文档和功能提交可以推进 main，但这个标签不移动。它表示内部调查闭环与交接基线，不代表真实模型准确率、公开调查 API 或网站部署完成。

main 为稳定分支；feature/backend、feature/frontend 为两条团队协作线。Phase 13-A 的代码差异仅为工程检查和文档；所有原业务文件保留。交接包修正一处等价递归类型写法并同步校验值，JSON Schema/wire 字段不变。

## 一次任务怎么走

~~~text
git fetch origin
git switch feature/frontend
git pull --ff-only origin feature/frontend
git switch -c frontend/yourname-investigation-view
~~~

实现后在个人分支提交、推送，打开 PR 到 feature/frontend。后端对应 feature/backend。两条协作线准备进入稳定版时，再向 main 开 PR。先确认目标分支，没有权限时先接受仓库邀请。

每个 PR 都填写模板，并查看 **Repository safety**、**Backend unit and contracts**、**Frontend tests and types**。作者不能用历史日志替代当前 CI；别人新增提交后必须查看最新提交的结果。合并决定由负责人明确执行，不开启 auto-merge。

本分支的 CI 在所有目标分支的 PR 创建/更新时运行，也在 main 推送和手动运行时执行。此前只覆盖 main、feature/backend、feature/frontend，导致标注工作使用的两份堆叠 PR 没有触发检查；本次去掉目标分支筛选，保留三项检查、只读权限和显式手动触发。个人分支直接 push 后，请创建/更新 PR 或手动运行检查；不会同时重复运行 push/PR 检查。此配置进入对应目标分支后才对该分支生效。

## 同步与冲突

个人分支保存自己的工作后再同步目标分支；共享分支不强制重写历史。冲突由涉及模块的负责人解决，关注字段删除、状态含义、证据引用和契约差异。没有队友授权不能覆盖其未完成内容。

## GitHub 当前限制

GitHub Actions 已可用，workflow token 权限为 read，不能批准 PR。工作流额外限制 contents: read，checkout 不保存认证信息，没有生产 Key、部署步骤或真实模型调用。

私有仓库的分支保护和 rulesets 查询均返回 **403：需 GitHub Pro 或公开仓库**。本任务不升级套餐、不变更公开性，因此 main **没有 GitHub 强制保护**。CONTRIBUTING 中的审查要求是当前团队规范。

## 发布与回溯

新增版本先审查和验收，再为指定提交建立新标签；不复用或移动旧标签。需要复现当前基线可以在单独目录/分支检出 v1.0-phase11D。发布说明须同时写明 API 暴露情况、数据模式、真实模型与 Benchmark 状态。

新前端构建工具或应用 TypeScript 迁移须单独授权，在其阶段增加真正的 install/typecheck/build；本阶段不能用“空构建成功”替代应用构建。

官方参考：[工作流触发](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)、[按 SHA 引用 Action](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/find-and-customize-actions)、[受保护分支](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)。
