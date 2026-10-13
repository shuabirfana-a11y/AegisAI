# Phase 13-E 实验登记准备

本目录只有准备模板，没有实验结果。`pilot-v0.1.template.json` 不被 Runner 自动读取，不能直接当冻结配置或运行回执。默认首批10个合格 HUMAN_GOLD；49题全部完成后另建完整数据版本。不能把5个公告簇衍生的49题当49个独立漏洞。

真实参数、凭据和库存绑定保存在 ignored `evaluation/experiments/local/`。API Key 只进本机环境，不填写模板、源码、Git或前端。当前模型 tag/Prompt版本仅来自历史运行记录；`latest`不是不可变模型版本，不能仅记 tag 就称为模型已冻结。

批准后为每次实验建立独立目录，保留 preflight、冻结配置、原模型文件摘要或服务版本回执、Prompt文件摘要、Git提交及干净状态、开始/结束时间、输出/失败/取消状态和原 Runner 的 experiment.json。模型/Prompt标识从持久化 Trace 对照冻结记录，发生漂移则记录 CONFIG_DRIFT，不发布该轮正式指标，也不删除失败材料。

本轮不创建企业库存，不导入外部 DRAFT，不替人工批准，不构造公平对照结果。操作步骤见 `docs/phase13e/EXPERIMENT_RUNBOOK.md`。
