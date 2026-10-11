# Phase 8 Preflight

输入：sources/phase8_request.txt（59节），input_manifest.json冻结595份前阶段资料；document_inventory.json登记121份Markdown全文读取记录。重点复核ASSET_MODEL、VERSION_MODEL、DOMAIN_MODEL、ASSET_RISK_UX以及Phase6/7实现与Tool V1。当前资料中SBOM延期条款由本次明确范围覆盖，旧文档保持历史原样。

实际开发库：aegis_phase6，55436，迁移0002。278漏洞、268包标识、527范围（252 parsed / 275 unsupported）、369原文、36 Claim、60 Evidence、61核验、6历史冲突。Asset/Component/Match三表存在，当前均0条。

|依赖|状态|落实方式|
|---|---|---|
|产品规范化/PackageIdentifier/PURL|PASS，范围有限|复用产品表及显式注册；禁跨生态和模糊合并|
|Version Parser|PARTIAL|PyPI PEP440可用；SemVer/Git/Maven等不套用PyPI|
|Version Matcher|PARTIAL|复用Phase7 intervals/contains，新增资产验证门控和可解释输出|
|真实Affected/Fixed|PASS，可信度不齐|527范围；MLflow3.15.0已确认fixed，两个范围冲突；不能伪造确认|
|PoC/KEV/EPSS/Patch/Evidence|PASS|读取现有实体与当前Claim/Evidence，未知不改false|
|Asset表|PASS|复用三表，增加必要库存/事件/风险快照及队列表，发布0003|
|前阶段Benchmark|PARTIAL|Phase7有28条待人工标签；此阶段不伪造gold|

真实数据生态：PyPI48、unknown214、NuGet4、Maven1、RubyGems1；未见npm。确定性比较首版支持PyPI，其余生态保留身份且返回UNKNOWN；不因未知而隐藏组件。

用户未提供其生产库存。本次真实案例使用明确标记is_demo的本地登记库存，匹配数据库中的真实公开漏洞；不称用户真实生产资产。

正式实现前隔离测试库与开发库。只给开发库执行追加0003，迁移往返仅专用空测试库。
