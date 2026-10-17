# 限定代码复审

按现有代码复审技能使用独立 reviewer，对本阶段的 literal 归一化、Request Builder、模板、模型 Schema 和隔离边界进行审查，不另建业务开发 Agent。

首次发现：公告影响范围和修复版本可能被误当部署版本；句末句号留入版本；前一句公告范围会影响后一句明确部署版本；Backend 冻结 Scope 与新归一化目标可能不一致。

修复后复核：17 项针对性控制通过，确认范围/修复信息保持未知、明确部署信息保留、输入冲突拒绝、Backend 不扩展已冻结 Scope。复审没有调用真实模型、API 或数据库。

最后补充的模型 Schema 限制只防止事实题请求无关的缺失部署版本；先保存失败控制，再修复，通过 67 项针对性回归、583 项 portable、128 项 evaluation 和契约检查。原 Service/context/Validator、专业 Agent、Runtime、Risk/Gate 均无变化。

复审和自动测试只证明这些边界的覆盖；真实 5 题执行结果以 diagnostic5 的原始记录为准，不把 Mock 测试当模型成功证据。
