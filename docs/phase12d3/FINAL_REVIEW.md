# 最终独立审查及处理

审查范围：1537ffdc36a52e6d5aaec876534d70cec5d62d43..5a994ba7a2075a6141c1d4b13600dbe935a642c1。一次独立只读整体审查；没有二次审查。Critical 0，Important 3，Minor 0。

| 问题 | 处理 | 复现测试 |
|---|---|---|
| 老库存空生态被当作显式身份冲突 | 未知生态作为缺省输入；通过既有精确包 ID 解析，不读新库存补版本 | test_legacy_inventory_null_identity_fields_use_exact_registered_package |
| 封存路径遗漏 qualifiers/subpath 适用性限制 | 恢复原 _asset 的保守限制；不改身份服务或 Risk 规则 | test_qualified_inventory_preserves_explicit_applicability_boundary，分别覆盖两种限定和登记/未登记 |
| 事务结束后读取过期 ORM ID 导出失败 | 使用事务内已保存的标量资产/组件 ID | test_demo_case_can_export_after_transaction_expired_inventory_objects |

修复前 6 个控制均真实失败。首次修复后旧库存和导出两项通过，限定身份的四项已返回 UNKNOWN，但测试误预期 REPLAN_REQUIRED。读取实际 Gate 审计发现，原 OBJECTIVE_PACKAGE_MISMATCH 是 FATAL，因此保持 FAILED 正确；只纠正测试预期，不改 Gate。最终通过记录见 verification.json。

审查确认：未发现跨用户/运行的回执授权绕过；失败任务仍拦截；证据状态须绑定自己的支持/冲突关系；缺失观察不会从新库存填补；空扩展不改变历史序列化；契约 manifest 14 项哈希吻合。

审查保留意见与裁定：

- 最初两个相同发行包使用不同 UUID 的限定身份复现不符合数据库唯一约束，不作为生产问题证据。采用符合单个包 ID 约束的控制验证保守边界；不能宣称正常导入已证实可利用。
- 企业扫描、利用条件和 Benchmark 准确率没有审查或评测证据。本轮结果只证明工程数据交接与明确范围的演示调查，不能推广为企业就绪或准确率达标。

没有延后的小问题。完整测试中首次瞬时失败仍保留，没有把尚未诊断的原因写成已查明。
