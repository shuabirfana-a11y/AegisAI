# 冻结准备配置

`experiment-001-prepared.json`是首轮执行规范及摘要登记；不是后台服务自动加载的配置。数据39人审金标已冻结，模型磁盘制品摘要已校验，温度/超时为计划值。实际服务和真实库存未联系或核对。本轮execution=false，禁止运行。

`report-template.json`仅空模板，无指标。旧默认manifest仍保留0金标历史；选择新数据必须显式用 `evaluation/datasets/AegisBench-v0.3-human39-20261013/manifest.json`。

没有API Key或数据库密码。未来认证只放本机AEGIS_ASSET_TOKEN，库存绑定放ignored local目录；标准答案不能进入Prompt/Retrieval/Context。新源commit和摘要配置只在准备分支；依赖PR尚未默认合并，不宣称main已同步。
