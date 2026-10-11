# 第三方数据组件调查

2026-10-03实时GitHub API元数据/README/LICENSE；Stars仅为当日参考，不代表正确性/安全。所有候选本轮重新联网；许可证表根据实际文本，API缺失时标未知。本轮没有安装业务依赖或复制第三方代码。

| Repository | 用途 | License | Stars快照 | 最近维护（push非SLA） | 直接依赖/参考决定 | 复制代码 | 风险 |
|---|---|---|---|---|---|---|---|
| [CVEProject/cve-schema](https://github.com/CVEProject/cve-schema) | CVE JSON schema版本/字段验证 | CC0-1.0 | 446 | 2026-01-30T20:57:39Z；archived=False | 后续仅用schema；不复制业务代码 | 否（本轮） | schema新增需保留raw，不能按日期猜版本 |
| [CVEProject/cvelistV5](https://github.com/CVEProject/cvelistV5) | 官方CVE获取/容器与Git增量设计 | CVE Terms of Use | 3026 | 2026-10-03T05:36:26Z；archived=False | 官方数据读取；不依赖程序库 | 否（本轮） | 数据归CVE条款，不继承schema CC0 |
| [google/osv.dev](https://github.com/google/osv.dev) | OSV API/schema/导出机制 | Apache-2.0代码；上游数据各许可 | 2956 | 2026-10-02T04:17:36Z；archived=False | 只参考设计，不部署整个平台 | 否（本轮） | 聚合许可/lineage；版本生态不能都按SemVer |
| [google/osv-scanner](https://github.com/google/osv-scanner) | OSV客户端/包生态查询组织 | Apache-2.0 | 11133 | 2026-10-02T20:58:00Z；archived=False | 参考客户端设计，不安装完整扫描工具 | 否（本轮） | 不是Collector；不运行资产扫描 |
| [cisagov/kev-data](https://github.com/cisagov/kev-data) | KEV格式/schema与更新记录 | CC0-1.0 | 124 | 2026-10-02T20:23:41Z；archived=False | 使用数据schema；普通JSON即可，不加parser依赖 | 否（本轮） | JSON元数据NOASSERTION须读README |
| [FIRSTdotorg/epss](https://github.com/FIRSTdotorg/epss) | 历史EPSS查询例/建模代码 | MIT代码；分数数据授权另核 | 31 | 2022-06-01T13:23:43Z；archived=False | 只参考接口形态，不依赖旧项目 | 否（本轮） | push为2022，当前API/数据指向应以2026官方文档为准 |
| [vehemont/nvdlib](https://github.com/vehemont/nvdlib) | NVD client与分页参数 | MIT | 117 | 2026-09-27T16:26:37Z；archived=False | 暂不直接依赖，按需参考源码 | 否（本轮） | 当前NVD规则与wrapper历史默认不一定一致 |
| [kurtmckee/feedparser](https://github.com/kurtmckee/feedparser) | RSS/Atom解析 | BSD-2-Clause源码（实际LICENSE） | 2433 | 2026-09-07T22:29:38Z；archived=False | 第二批计划直接依赖；本轮不安装；不复制 | 否（本轮） | 只解析已受控下载bytes，不让库从任意URL自动获取；feed窗口有限 |
| [pypa/packaging](https://github.com/pypa/packaging) | PyPI PEP440 Version/Specifier | Apache-2.0 OR BSD-2-Clause | 751 | 2026-10-02T17:47:10Z；archived=False | 首期计划直接依赖；本轮不安装；不复制 | 否（本轮） | Specifier预发布策略与OSV边界须显式处理，last_affected不能猜fixed |
| [package-url/packageurl-python](https://github.com/package-url/packageurl-python) | PURL身份解析 | MIT（mit.LICENSE已另取） | 91 | 2026-03-11T23:55:06Z；archived=False | 首期计划直接依赖；本轮不安装；不复制 | 否（本轮） | inferred URL不能授予网络权限；不凭PURL强转CPE |
| [aboutcode-org/univers](https://github.com/aboutcode-org/univers) | 多生态版本范围 | UNKNOWN / NEED_VERIFY：本轮API未找到许可证正文 | 50 | 2026-05-01T16:39:15Z；archived=False | 暂缓依赖/复制，参考需求范围 | 否（本轮） | 必须逐文件核许可；全生态支持不先承诺 |
| [nilp0inter/cpe](https://github.com/nilp0inter/cpe) | CPE2.3解析 | LGPL-3.0 | 95 | 2025-09-23T08:44:07Z；archived=False | 暂缓依赖/复制 | 否（本轮） | 维护push2025-09；首期不需要，LGPL集成方式后续审阅 |
| [oasis-open/cti-python-stix2](https://github.com/oasis-open/cti-python-stix2) | STIX对象/校验 | BSD-3-Clause | 438 | 2026-02-12T06:21:36Z；archived=False | 仅设计参考；STIX交换需求出现后依赖 | 否（本轮） | STIX不替代业务Evidence/Claim；不能按类名认事实可信 |
| [OpenCTI-Platform/connectors](https://github.com/OpenCTI-Platform/connectors) | CTI适配器/任务调度/增量state组织 | Apache-2.0 | 582 | 2026-10-03T02:48:26Z；archived=False | 只参考设计，不fork，不复制 | 否（本轮） | 平台接口/依赖重；source licensing单独管理 |
| [OpenCTI-Platform/opencti](https://github.com/OpenCTI-Platform/opencti) | CTI关系/出处与任务设计 | CE Apache-2.0；EE专有许可（实际文件） | 10082 | 2026-10-03T02:01:19Z；archived=False | 只参考设计，不fork，不复制 | 否（本轮） | 逐文件CE/EE边界；不得误记整个当前仓库AGPL或全Apache |
| [intelowlproject/IntelOwl](https://github.com/intelowlproject/IntelOwl) | 分析器/任务/失败隔离 | AGPL-3.0 | 4737 | 2026-10-01T08:30:19Z；archived=False | 只参考设计，不fork，不复制 | 否（本轮） | 外部API/工具和copyleft边界；未知分析脚本不执行 |
| [cve-search/cve-search](https://github.com/cve-search/cve-search) | CVE/NVD导入及更新参考 | AGPL-3.0 | 2653 | 2026-09-30T07:54:31Z；archived=False | 只参考设计，不fork，不复制 | 否（本轮） | 不能假记GPL/MIT；平台多服务依赖和许可传播 |
| [MISP/MISP](https://github.com/MISP/MISP) | 情报对象/来源与事件组织 | AGPL-3.0 | 6563 | 2026-10-02T15:53:38Z；archived=False | 只参考设计，不fork，不复制 | 否（本轮） | 不按公开可读就复制代码/部署改皮；对象关系不当事实认证 |

源码只读检查：nvdlib/cve.py核API参数/日期窗口组织，feedparser/api.py核请求/解析职责；没有执行下载源码。原文与hash在evidence/urls中。核心3源使用官方结构/常规JSON读取即可，不为了parser包装再引入多个冷门client。现阶段冻结计划依赖仅packaging、packageurl-python，RSS批次再用feedparser；NVD/KEV/EPSS不默认安装第三方client。

更新当前许可事实：OpenCTI当前CE为Apache-2.0、EE有商业条款；IntelOwl/MISP/cve-search本轮均AGPL-3.0。仅参考设计时不复制表达/代码；若未来真要依赖/复制，重新锁定版本、逐文件license/notice、兼容性和SBOM，再决定，不能因Stars多省略。
