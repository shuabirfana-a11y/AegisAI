# 资产及组件模型

Asset保存server owner、name/type/is_demo、environment/exposure/description。Component保存精确包/Product FK、原始版本、规范版本、PURL、ecosystem/namespace、source、inventory_key、revision、first_seen/last_seen和规范化理由。version未知也允许保存，不能补成受影响/安全。

版本变更增加revision，旧Match/Snapshot不可覆盖。包身份改变不能破坏旧FK，因此软移除旧组件、创建新的组件。SBOM同asset更新权威SBOM来源清单，manual组件独立保留；移除历史解释风险不再出现在当前清单的原因。
