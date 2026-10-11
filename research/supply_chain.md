# 资产与供应链：复用扫描器，延后重型平台

**V0.1 不做完整 SBOM/镜像扫描服务。** 先证明一个已锁定 PyPI 包版本与漏洞范围能确定匹配；V0.2 复用 Syft/OSV-Scanner，而不是自己写镜像和依赖扫描器。

| 输入 | 可复用方案 | 易误判点 | 阶段 |
|---|---|---|---|
| requirements.txt | 解析 PEP 508/440；OSV-Scanner 对受支持文件模式扫描 | `>=`/未固定依赖不是已安装版本；递归 -r、URL/VCS 依赖、markers/extras | V0.1 单个明确包版本；批量/完整解析 V0.2 |
| package-lock | OSV-Scanner、PURL/生态规范 | 依赖路径、多个版本、workspace、dev/optional、实际部署用途 | V0.2 |
| CycloneDX/SPDX SBOM | 格式校验+规范导入；扫描器作对照 | 缺包生态/版本、过时 SBOM、生成环境不同；不同标准版本支持差异 | V0.2 |
| Docker 镜像 | Syft OCI/归档→SBOM；Grype/OSV-Scanner 匹配 | 发行版 backport、层、tag 可变、权限/磁盘，不能默认挂 Docker socket | V0.2 |
| 项目目录 | Syft 包发现、OSV-Scanner 锁文件 | 项目脚本不能执行；路径、symlink、归档炸弹、私有依赖外发 | V0.2 |
| 模型文件 | ModelScan 静态扫描补充来源 | pickle/模型加载可能执行代码；静态扫描不保证无后门 | V0.2/决赛隔离实验 |

依据：[Syft](https://github.com/anchore/syft)、[Grype](https://github.com/anchore/grype)、[OSV-Scanner](https://github.com/google/osv-scanner)、[CycloneDX](https://github.com/CycloneDX/specification)、[SPDX](https://github.com/spdx/spdx-spec)。每个工具的输入格式支持应以锁定 release 的文档/实际验收为准，本轮没有运行镜像扫描。

## Asset→Package→Version→Vulnerability

资产记录含 asset ID、tenant/scope、采集时间、镜像 digest/锁文件 hash、工具版本、证据位置；组件以生态+PURL+版本标识，保留依赖路径和用途。用 OSV/生态版本判断形成 affected/not_affected/unknown，再加入环境、暴露、运行条件、厂商发行版修订和 VEX。

Syft 做“发现安装了什么”；Grype/OSV-Scanner 做“按它们的数据源判断可能影响”；AegisAI 做“结合来源、正确生态、历史和证据解释为什么”。扫描结果不能直接盖章 verified，不同扫描器同用 OSV/NVD 时结果一致也不自动成为独立核验。

PURL 为包身份，不自动解决 PyTorch 产品别名，也不替代 CPE 的平台条件。OSV introduced=0 是该数据模式中的开始标记，不是随意构造真实版本字符串；GIT range 用 commit 信息。未知/未锁定版本必须返回 unknown，不能用版本字符串排序猜测。

## OpenVEX 与 GUAC

[OpenVEX](https://github.com/openvex/spec) 用于记录 affected/not_affected/fixed/under_investigation 等有依据声明，保留 justification、timestamp、publisher、scope。来源可信且与具体资产匹配的 VEX 可支持解释或抑制；不能把任意用户上传的 not_affected 文件当事实覆盖所有结果。

[GUAC](https://github.com/guacsec/guac) 的供应链证据关联设计值得借鉴，归 C；暂不部署图系统。V0.1 的 PostgreSQL 关联与 evidence 足够表达有限包关系，等真实多来源供应链查询出现再评估图基础设施。

## 工具运行的最小权限

V0.2 的 scanner worker 与主服务分离，非 root、只读输入卷、隔离输出、时间/CPU/内存/解压/磁盘限制、受控网络与离线数据库快照。镜像按 digest 取证。不得执行 repo 安装脚本、PoC、模型反序列化或用户提供命令。联网 scanner 可能把包名/版本提交到 OSV；企业私有清单默认不外发，需提供离线策略。许可见 [licenses.md](licenses.md)，矩阵见 [security_review.md](security_review.md)。

## 候选档案

所有时间来自本次快照。资源和部署级别为选型估计，没有冒充部署实测。原始 JSON 见 [候选清单](candidate_catalog.json)。

### anchore/grype · B

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/anchore/grype)；https://github.com/anchore/grype（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | supply_chain；资产与漏洞数据库匹配 |
| 能力 / 接入 / 语言 | 资产与漏洞数据库匹配；CLI；Go |
| License | Apache-2.0；[授权来源](https://github.com/anchore/grype/blob/4759e396277871feb6530dcc45ae9d3acd074980/LICENSE) |
| 最近更新 / Star | 2026-10-02T14:12:23Z；12965（快照统计，不作为质量结论） |
| Release | v0.120.0；2026-10-02T14:23:18Z；https://github.com/anchore/grype/releases/tag/v0.120.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 3 个 Issue；最近样本更新 2026-10-02T20:27:33Z；API open_issues_count=417（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | B；V0.2 对照扫描；保留数据库快照，分清发行版 backport 与普通包版本 |
| 核查来源 | [README/文档](https://github.com/anchore/grype/blob/4759e396277871feb6530dcc45ae9d3acd074980/README.md)；源码 SHA 4759e396277871feb6530dcc45ae9d3acd074980；README 已下载 |

### anchore/syft · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/anchore/syft)；https://github.com/anchore/syft（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | supply_chain；镜像、目录与文件的 SBOM/包发现 |
| 能力 / 接入 / 语言 | 镜像、目录与文件的 SBOM/包发现；CLI；Go |
| License | Apache-2.0；[授权来源](https://github.com/anchore/syft/blob/bc68299565d1d2bc7f54159db2f1eb5567144aff/LICENSE) |
| 最近更新 / Star | 2026-10-02T13:30:02Z；9632（快照统计，不作为质量结论） |
| Release | v1.54.0；2026-10-01T20:54:29Z；https://github.com/anchore/syft/releases/tag/v1.54.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-10-02T18:48:05Z；API open_issues_count=646（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | A；V0.2 直接 CLI，不重写清单扫描器；无 root/docker socket 的隔离任务 |
| 核查来源 | [README/文档](https://github.com/anchore/syft/blob/bc68299565d1d2bc7f54159db2f1eb5567144aff/README.md)；源码 SHA bc68299565d1d2bc7f54159db2f1eb5567144aff；README 已下载 |

### CycloneDX/specification · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/CycloneDX/specification)；[官网](https://cyclonedx.org/) |
| 类别 / 解决问题 | supply_chain；SBOM、依赖与安全信息标准 |
| 能力 / 接入 / 语言 | SBOM、依赖与安全信息标准；Data；XSLT |
| License | Apache-2.0；[授权来源](https://github.com/CycloneDX/specification/blob/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/LICENSE) |
| 最近更新 / Star | 2026-09-24T16:01:39Z；556（快照统计，不作为质量结论） |
| Release | 1.7.2；2026-09-17T12:31:18Z；https://github.com/CycloneDX/specification/releases/tag/1.7.2 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-10-02T15:58:05Z；API open_issues_count=230（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | A；V0.2 首选交换格式；选择工具共同支持版本，不为追最新而升级 |
| 核查来源 | [README/文档](https://github.com/CycloneDX/specification/blob/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/README.md)；源码 SHA 1ce97b2a7b8cf2429da248560d2aa671c6bce74a；README 已下载 |

### google/osv-scanner · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/google/osv-scanner)；[官网](https://google.github.io/osv-scanner/) |
| 类别 / 解决问题 | supply_chain；lockfile/SBOM 的 OSV 漏洞扫描 |
| 能力 / 接入 / 语言 | lockfile/SBOM 的 OSV 漏洞扫描；CLI；Go |
| License | Apache-2.0；[授权来源](https://github.com/google/osv-scanner/blob/1b86129be1f0285c403616cb362ac188de676c6e/LICENSE) |
| 最近更新 / Star | 2026-10-02T05:16:32Z；11133（快照统计，不作为质量结论） |
| Release | v2.6.0；2026-09-14T02:55:16Z；https://github.com/google/osv-scanner/releases/tag/v2.6.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-10-02T17:01:38Z；API open_issues_count=103（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 中 / 中；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | A；V0.2 Python/JS 主线直接 CLI；对照自有匹配，不能外发私有清单默认开启 |
| 核查来源 | [README/文档](https://github.com/google/osv-scanner/blob/1b86129be1f0285c403616cb362ac188de676c6e/README.md)；源码 SHA 1b86129be1f0285c403616cb362ac188de676c6e；README 已下载 |

### guacsec/guac · C

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/guacsec/guac)；[官网](https://guac.sh) |
| 类别 / 解决问题 | supply_chain；供应链证据连接与图模型 |
| 能力 / 接入 / 语言 | 供应链证据连接与图模型；API / SDK / Docker（见专题选择）；Go |
| License | Apache-2.0；[授权来源](https://github.com/guacsec/guac/blob/fd86ccd19863ae5f6b019e151cb07444302c03cc/LICENSE) |
| 最近更新 / Star | 2026-09-29T11:18:26Z；1548（快照统计，不作为质量结论） |
| Release | v1.1.0；2026-03-13T18:37:52Z；https://github.com/guacsec/guac/releases/tag/v1.1.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 4 个 Issue；最近样本更新 2026-10-02T14:38:24Z；API open_issues_count=72（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 高 / 高；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；服务/API 模式可能需要；以专题区分匿名/令牌，不存于报告 |
| 权限 / 风险 | 网络与本地工作目录；外部凭证/写入/传输限制见 security_review.md；MEDIUM；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | C；借鉴证据关系；首期无需图数据库和大规模供应链基础设施 |
| 核查来源 | [README/文档](https://github.com/guacsec/guac/blob/fd86ccd19863ae5f6b019e151cb07444302c03cc/README.md)；源码 SHA fd86ccd19863ae5f6b019e151cb07444302c03cc；README 已下载 |

### openvex/spec · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/openvex/spec)；https://github.com/openvex/spec（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | supply_chain；VEX 状态与影响声明格式 |
| 能力 / 接入 / 语言 | VEX 状态与影响声明格式；Data；数据/多语言或 API 未给出 |
| License | CC0-1.0；[授权来源](https://github.com/openvex/spec/blob/61b5f885d0f481f48683c93345e49ef1a6e9fdff/LICENSE) |
| 最近更新 / Star | 2026-09-09T19:51:21Z；192（快照统计，不作为质量结论） |
| Release | v0.2.0；2023-08-22T18:29:58Z；https://github.com/openvex/spec/releases/tag/v0.2.0 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 3 个 Issue；最近样本更新 2026-08-31T18:55:08Z；API open_issues_count=24（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | A；V0.2 记录审阅后的不受影响理由；声明不能无条件覆盖扫描结果 |
| 核查来源 | [README/文档](https://github.com/openvex/spec/blob/61b5f885d0f481f48683c93345e49ef1a6e9fdff/README.md)；源码 SHA 61b5f885d0f481f48683c93345e49ef1a6e9fdff；README 已下载 |

### package-url/packageurl-js · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/package-url/packageurl-js)；[官网](https://www.npmjs.com/package/packageurl-js) |
| 类别 / 解决问题 | supply_chain；JavaScript PURL SDK |
| 能力 / 接入 / 语言 | JavaScript PURL SDK；SDK；JavaScript |
| License | MIT；[授权来源](https://github.com/package-url/packageurl-js/blob/4cfc3681c245c6346e2bef3f3e6a54f011203960/LICENSE) |
| 最近更新 / Star | 2026-08-24T16:11:47Z；30（快照统计，不作为质量结论） |
| Release | 无 GitHub Release（HTTP 404；不代表无包发布） |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 2 个 Issue；最近样本更新 2026-05-05T20:08:12Z；API open_issues_count=9（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；工程 |
| 最终建议 | A；有 JS 处理组件时使用；纯 Python 首期不额外引入 |
| 核查来源 | [README/文档](https://github.com/package-url/packageurl-js/blob/4cfc3681c245c6346e2bef3f3e6a54f011203960/README.md)；源码 SHA 4cfc3681c245c6346e2bef3f3e6a54f011203960；README 已下载 |

### package-url/packageurl-python · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/package-url/packageurl-python)；https://github.com/package-url/packageurl-python（未见独立官网，项目主页作为入口） |
| 类别 / 解决问题 | supply_chain；Python PURL 解析、构造与规范化 |
| 能力 / 接入 / 语言 | Python PURL 解析、构造与规范化；SDK；Python |
| License | MIT 核心；thirdparty 中有其他授权；[授权来源](https://github.com/package-url/packageurl-python/tree/c7c7b46346eebcd86ec61d4ee7c6a84c3fe5fcc4) |
| 最近更新 / Star | 2026-03-11T23:54:36Z；91（快照统计，不作为质量结论） |
| Release | v0.17.6；2025-11-24T15:20:20Z；https://github.com/package-url/packageurl-python/releases/tag/v0.17.6 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-08-28T10:43:17Z；API open_issues_count=68（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 本地输入解析；无须高权限，安装依赖另审；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；工程 |
| 最终建议 | A；V0.1 直接 SDK；核心 MIT，第三方授权随包保留 |
| 核查来源 | [README/文档](https://github.com/package-url/packageurl-python/blob/c7c7b46346eebcd86ec61d4ee7c6a84c3fe5fcc4/README.rst)；源码 SHA c7c7b46346eebcd86ec61d4ee7c6a84c3fe5fcc4；README 已下载 |

### package-url/purl-spec · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/package-url/purl-spec)；[官网](https://packageurl.org/) |
| 类别 / 解决问题 | supply_chain；跨生态软件包身份表达 |
| 能力 / 接入 / 语言 | 跨生态软件包身份表达；Data；Python |
| License | MIT（实际 LICENSE）；[授权来源](https://github.com/package-url/purl-spec/blob/7cd2d3442fb9c88155db17ada7c911b40ec22d41/LICENSE) |
| 最近更新 / Star | 2026-09-29T22:26:05Z；1116（快照统计，不作为质量结论） |
| Release | v1.0.1；2026-08-03T22:49:35Z；https://github.com/package-url/purl-spec/releases/tag/v1.0.1 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 1 个 Issue；最近样本更新 2026-09-20T17:48:00Z；API open_issues_count=231（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | A；核心身份编码；PURL 不是产品别名解析，也不自动替代 CPE |
| 核查来源 | [README/文档](https://github.com/package-url/purl-spec/blob/7cd2d3442fb9c88155db17ada7c911b40ec22d41/README.md)；源码 SHA 7cd2d3442fb9c88155db17ada7c911b40ec22d41；README 已下载 |

### spdx/spdx-spec · A

| 字段 | 核查结果 |
|---|---|
| GitHub / 官网 | [项目](https://github.com/spdx/spdx-spec)；[官网](https://spdx.github.io/spdx-spec/) |
| 类别 / 解决问题 | supply_chain；软件物料与许可信息标准 |
| 能力 / 接入 / 语言 | 软件物料与许可信息标准；Data；Python |
| License | Community-Spec-1.0 / 既有部分 CC-BY-3.0 / 脚本 MIT；[授权来源](https://github.com/spdx/spdx-spec/blob/b0f290ffdb31b5682ff90bd99636d1d29e79d3b2/LICENSE) |
| 最近更新 / Star | 2026-09-23T05:11:48Z；386（快照统计，不作为质量结论） |
| Release | 3.0.1；2024-12-17T18:58:27Z；https://github.com/spdx/spdx-spec/releases/tag/3.0.1 |
| Issue / 维护 | 近 6 个 issue/PR 返回条目过滤 PR 后有 0 个 Issue；本页无 Issue 样本，不能推断无人维护；API open_issues_count=134（含 PR）；2026 年有提交；仅证明活动，不保证支持质量 |
| 部署 / 资源 | 低 / 低；场景估计，未部署测量；manifest 内存不是实测峰值 |
| 收费 / Key | 代码本身无订阅费；数据条款独立；自托管与模型调用成本自担；公共数据/本地 SDK 不需要 |
| 权限 / 风险 | 结构化公共数据下载；文件读取与解析，不执行引用内容；LOW；数据/SDK 接入或未受控部署的场景等级；非漏洞认证，详见安全报告 |
| AegisAI 模块 / 比赛价值 | supply_chain；创新 / 工程 / 问答 |
| 最终建议 | A；接受其导入/导出；规范 Community-Spec 等授权与脚本 MIT 分开 |
| 核查来源 | [README/文档](https://github.com/spdx/spdx-spec/blob/b0f290ffdb31b5682ff90bd99636d1d29e79d3b2/README.md)；源码 SHA b0f290ffdb31b5682ff90bd99636d1d29e79d3b2；README 已下载 |
