# 第三方决定

与research的A/B/C/D意义不同，本阶段分类按时间：A=V0.1直接采用，B=V0.1封装接入，C=V0.2，D=决赛增强，E=当前放弃。全部87个原候选逐项重分类、理由、替代、估算代码量、复杂度、许可/安全/维护和单点记录在third_party_decisions.json。估算是工作量判断，不是实测LOC。

现在采用：CVE List V5/OSV/CISA KEV（B），CVE/OSV schema与PURL/packageurl-python/packaging（A）。KEV由用户最新总路线提升到首批；CISA ADP直接从CVE解析，独立Vulnrichment仓库仍延后对账。基础框架栈见TECH_STACK。feedparser/Jina/Extractor/Dify放C；node-semver放C。

现在不采用大型平台和MCP，仅保留研究参考；停止维护/许可不清/通用SQL或第三方聚合权限过大的项目放E。不能因为只省几十行请求包装就增加Server；更不能因为不用官方数据API就企图自行维护全量漏洞知识。

CVE和OSV服务可能不可用：已有raw快照与状态允许延迟/回补；OSV不可用时包范围unknown，不能猜；CVE源身份/撤销对账不可达就显示last_success/stale。没有额外云服务SPOF；数据库和blob是本部署单点，必须备份恢复。源JSON复制和网站条款、代码复制和设计参考分别管理。
