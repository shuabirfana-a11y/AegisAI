# 资产组件与影响结果

Asset是人工授权的服务/项目/环境，owner_principal由认证层供给，is_demo区分演示。AssetComponent保存Product/精确生态包/原始包名/版本、manual/sbom/scanner来源和inventory_revision；包身份未解析可null，raw version可以2.x，但影响不能假判确定。当前没有SBOM/扫描器或互联网发现业务。

AssetVulnerabilityMatch不可变追加，保存component/vulnerability、matched_range/package、三态affected/not_affected/unknown、当时版本、库存修订、Claim修订、matcher版本/理由及检测/评估时间。复合FK保证范围属于同漏洞/包，包也属于该组件；确定结论必须给范围，未知可以没有范围。not_affected只针对当前漏洞、当前包版本与查询范围，不是“资产整体安全”。

组件库存改变后旧结果保留，当前查询只使用匹配component_revision=inventory_revision且版本/scope/Claim仍适用的结果；不一致返回stale/unknown并需重算。匹配范围FK防跨包，但Claim与范围的业务一致性、授权、所有范围union完整性和撤销传播由第6阶段写入事务验证，当前未实现比较器。

不按CVSS×EPSS乘积造综合风险。优先级解释展示精确版本、KEV已收录、PoC可信关联及修复依据；缺任意信号明确unknown。Asset/Match/Review保持P1，不能因本轮建表宣称完整初赛P0已交付。Fixture的affected结果是人为给定存储样例，不是实际算法预测或评测真值。

Asset与Component软删保留历史；Match append-only，不级联删除。owner与请求scope由后续认证授权过滤；数据库表没有开放资产API。测试覆盖有效范围、错误包范围被拒、未知没有伪范围以及删除主情报不破坏Evidence，尚未测试真实互联网资产或SBOM大数据性能。
