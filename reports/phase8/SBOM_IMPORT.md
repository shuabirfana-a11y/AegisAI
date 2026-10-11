# SBOM导入与标准

实际支持CycloneDX JSON1.6和SPDX JSON2.3，不宣称所有版本/JSON-LD/XML支持。官方schemas原样保存在backend/app/resources/sbom，以jsonschema离线验证，remote retrieve禁用；document/source_ref/locator/SHA保留在库存事件。不执行名称/路径/$schema/PURL，也不上传代码。

2MiB、深度40、100000节点、1000组件、5秒解析检查；拒绝NaN、重复JSON键、矛盾重复ref/多个PURL、PURL版本/生态/包矛盾。所有组件先检查身份再写，事务整体回滚。再次导入返回added/updated/removed，原生ref优先，缺ref用规范身份；重复导入不制造组件库存修订。准确风险状态不因SBOM格式而改变。

Syft研究：Anchore官方本地SBOM生成工具（Apache2.0），可未来在项目/容器本地执行生成CycloneDX后导入。本机没有安装Syft，格式fixture足以验收Import，不将Syft当核心功能或自动上传用户代码。[CycloneDX schema](https://github.com/CycloneDX/specification/blob/1.6/schema/bom-1.6.schema.json)、[SPDX schema](https://github.com/spdx/spdx-spec/blob/v2.3/schemas/spdx-schema.json)、[Syft](https://github.com/anchore/syft)。
