# GitHub Pages 静态演示

演示入口：https://shuabirfana-a11y.github.io/AegisAI/

页面展示 C08、C09 已保存的真实 HTTP 调查记录、原始来源引用和源码下载，不连接实时模型或数据库。不能在该静态页面新建调查；真实运行方式见根目录 `QUICKSTART_WINDOWS.md`。

本交付分支保持后端基线 `4fddc5c40eb8231cb6e7a55f7f479035502b4ea9`，仅接入团队前端提交 `437cb844830116f638f6aaed66680e8de367e8c2` 修改的 14 个前端文件。没有合入该前端分支基线中的旧后端，没有修改 Gold、评分器、Gate 或 Verification。

新前端的情报监测、Agent 编排和知识底座包含显式演示数据。截图中的 864、631、141、99.2 等计数不是本次实际采集或实验成绩。调查工作台仍区分真实 API 与 Mock；没有公网后端时，请使用静态案例页查看历史记录，而非将 Mock 输出当作真实新调查。

静态页位于独立分支 `codex/github-pages-site`，该源码分支为 `codex/github-pages-final`。默认 `main` 和原冻结分支保留，没有合并或删除原分支。

静态页导出字段来自 `outputs/final-live-demo/live-C08.json`、`live-C09.json` 的原始保存记录，经字段白名单排除认证请求头、模型原始请求、人工评分和 Gold。记录时间、源文件指纹、源码版本分别保存在静态页发布清单中。

C25 备份、数据库、模型凭证和完整私有运行目录继续留在本地，不随静态站发布。Windows Worker 组合执行问题仍未解决，本次静态发布不能作为生产可靠性或新前端完整验收的证明。
