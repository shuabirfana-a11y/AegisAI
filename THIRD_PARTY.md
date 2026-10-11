# 第三方依赖与内容

Phase7未引入新的第三方代码项目或Python依赖；数据库、HTTP、API、版本解析沿用原实际环境。依赖版本/用途/许可取自安装分发，完整记录及许可证原件见 [Phase6依赖声明](reports/phase6/THIRD_PARTY_NOTICES.md) 和 reports/phase6/licenses/。

POC/Patch关联、Evidence、Verification与Conflict规则为本项目实现，未fork大型CTI平台。cvss为LGPLv3+，psycopg为LGPL3等沿用已记录许可，发布打包应保留其相应要求。GitHub/FIRST/CISA的元数据或少量引用仅用于开发追溯，上游数据授权与API条款不因存入DB而扩大；没有对外再发布抓取内容或下载执行候选仓库代码。

Phase8增加离线JSON Schema验证：jsonschema4.25.1、attrs26.1.0、jsonschema-specifications2025.9.1、referencing0.37.0、rpds-py2026.6.3，全部采用MIT许可。实际版本/用途来源与许可证原件见[依赖登记](reports/phase8/third_party_dependencies.json)和licenses/phase8/，requirements已锁定版本。

CycloneDX项目的1.6 BOM schema及其SPDX许可枚举依赖按Apache-2.0保留原文；JSF0.82 schema由Anders Rundgren/OpenKeyStore开发，原schema注明Apache-2.0。SPDX工作组2.3 specification的JSON schema采用CC-BY-3.0，保留SPDX署名、来源及许可证原件。全部schema未修改，出处与SHA256见[原件登记](reports/phase8/schema_sources.json)，文件和许可在backend/app/resources/sbom/。SPDX输入文档的dataLicense=CC0-1.0不等于该规范schema的许可证。

Syft仅做官方选型研究，未安装、未复制或执行其代码。资产/SBOM内容只在本地处理，不发送模型或外部接口。没有加入大型CTI平台、扫描器或依赖评测指标的第三方服务。
