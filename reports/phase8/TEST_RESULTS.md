# 实际工程测试

最终完整套件292 passed，0failed，0skipped，1项第三方AnyIO弃用警告（work/phase8_final_full.log）。初次279通过，独立审查后13项新增回归均已先失败再修复。包括官方schema导入/边界/恶意输入、精确identity、三态/核验冲突、版本升级、riskfactors/PoC变化、库存幂等/差量、owner鉴权、公开聚合无私有库存信息及无情报事件的针对性重算。49表/25不可变保护、实际migration0003往返、零ORM漂移。

不将规则fixtures或工程通过率当人工gold Accuracy/FalsePositive。
