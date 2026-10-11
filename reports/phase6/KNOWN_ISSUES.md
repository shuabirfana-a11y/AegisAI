# 已知边界与问题

1. CVE 是默认目录加种子的有限基线，OSV 是 PyPI 有限基线与 CSV 前 1000 行；两者均不是全库 CDC。OSV 前段若未跨完整 overlap 边界，水位保持旧值；更旧记录及 EMPTY/其他生态需后续调和。
2. KEV 已取完整目录并校验 count/唯一 CVE，但域数据只逐批处理。pending 与 normalized_catalog_version 明确暴露；目录完整下载不能宣传为所有条目已入库。
3. 外部网络会出现 ConnectTimeout/ReadTimeout/ConnectError、Git 元数据操作失败。完整历史失败保留，逐记录失败在 pending；本机实测延迟不能当部署环境 SLA。HTTP/Git 有单次边界，没有整个同步的硬截止时间。
4. 崩溃后 running 状态需人工确认再恢复，没有分布式租约或自动 stale-run 回收；同源多进程调度不在本阶段验证范围。当前按每来源顺序运行。
5. 产品注册表有限，相关性 V0 可漏报/误报；unknown 生态按来源/供应商隔离，不代表已建立完整全球产品库。SEMVER/GIT/复杂范围保留 unsupported，不提供资产风险结论。
6. 多 CVE 公告和已有不同候选之间的复杂历史归并需复核；只做无歧义单 CVE 的候选提升。不同来源可能同源转载，多源去重不等于独立证据或 Claim 核验。
7. Raw 的 native publish/modified 在解析前未知而为 null，解析后在 immutable observation 保存，API 给单独 native 字段。没有修改 Raw 以绕过历史保护。没有 raw 下载 HTTP 路由；离线 replay 通过数据库 raw UUID。
8. 引用仅保存 URL/来源，不下载页面；超过 2000 字节的 URL 留在 raw/observation，暂不写 B-tree 索引实体。没有 PoC 搜索/执行、Patch/commit 关联、EPSS、Vendor 新源、LLM/Agent/Dify。
9. 本地开发库 trust、只读 API 无认证、无 TLS/调度/生产监控。没有实际前后端联调；UI 原型仍明确 Mock。
10. 本机无 Docker，Compose 只静态核验，镜像构建/运行尚未验证。数据库备份/恢复、跨平台运行、规模并发压测不在当前实测结论内。
11. 测试有一项第三方 AnyIO alias 弃用警告；没有测试失败，不隐藏警告。cvss 3.6 是 LGPLv3+ 外部依赖，原始许可证留在 licenses/cvss，未修改/复制其实现。
12. OSV API 的同内容 JSON 键序会变化；本阶段按原始字节 hash 追加修订，可能产生语义相同的字段历史。updated 是字节变动计数，不代表新安全事实。没有额外加入语义摘要去压缩这些历史；旧 raw 不能覆盖或重排后冒充原文。纯重复原文字节的重放没有新增域记录。

已修复并留有失败记录/回归用例：gzip 二次解码、CVE promisor blob 获取失败的固定 commit HTTPS 方案、OSV 大索引超时后的明确前段采集、不完整发现窗口误推进水位、recheck 消失 backlog、未知产品供应商导致复合 FK 错配、无版本 KEV 详情未显示产品、PEP440 含端点单版本与严格空区间/SEMVER 错误语义。历史试跑使用初始开发实现；最终代码和文件 hash 在 artifact_manifest.json。

不发布 Precision/Recall/F1、问答准确率、POC/Patch 准确率或比赛 Benchmark；尚无人工 gold 和正式评测运行。完成 Phase 6 后停止，等待用户决定 Phase 7。
