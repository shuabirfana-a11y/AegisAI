# 资产风险架构

复用Phase5 Asset/AssetComponent/AssetVulnerabilityMatch，增加0003资产上下文、不可变库存事件/风险快照/风险变化与可重试队列。现有Phase6采集和Phase7核验不重新实现。identity→versions→matching→remediation/priority→risk各职责分离；inventory组织写入事务，GET queries只读；event queue消费现有IntelligenceEvent。无LLM、Dify、扫描器或PoC执行。

开发库55436与空测试库55435分离；实际0003→base→0003在测试库验证，49表/25历史保护/零ORM漂移。无Git仓库，基线和输出SHA256留痕。
