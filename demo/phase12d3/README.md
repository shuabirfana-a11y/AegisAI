# 资产风险链路复现

本目录验证真实本地模型、HTTP 调查和官方证据交接。资产为手工登记的 `is_demo=true` 库存，版本不是扫描结果；它不是人工 Ground Truth 或安全准确率评测。

## 准备条件

从项目根目录运行，使用已安装后端依赖的 Python。需要本机 PostgreSQL 的独立演示库、本机 Ollama 中已有的 `aegisai-qwen25-planner:latest`，以及现有 MiniLM Embedding 缓存。脚本不会下载模型。

`prepare_demo.py` 当前采用本机已授权的配置：PostgreSQL `127.0.0.1:55436`，本地角色 `aegis_local`，独立库 `aegis_phase12d3_demo`。其他电脑先把演示脚本中的本地连接配置调整为自己的独立演示库，不使用生产库或旧开发库。脚本不删除、清空或迁移旧项目库。

## 获取真实来源并登记演示资产

```text
python demo/phase12d3/prepare_demo.py
```

脚本获取 vLLM 官方 GHSA-hjq4-87xh-g4fv 公告和对应 OSV 记录，通过原有采集、版本标准化、证据和知识索引服务保存。官方 CVSS 向量、分数及严重性不一致或无向量时直接停止；不会用模型猜事实。已登录 GitHub CLI 时可在进程内复用凭据，凭据不写入文件。

实际导出的本机资产 ID 见 `work/phase12d3/generated-cases.json`，来源及时间见 `real-demo-inputs.json`。本目录 `cases.json` 保存历史验收用的 ID，不能照抄为其他电脑的库存 ID。

## 运行一次真实 HTTP 调查

在本机进程环境配置 `AEGIS_DATABASE_URL` 为上述独立演示库，显式配置 `AEGIS_ASSET_OWNER=phase12d3-demo-operator`。身份是登记时配置的演示操作者，不能从别人的资产记录自动切换。然后运行：

```text
python backend/scripts/probe_investigation_failures.py --cases work/phase12d3/generated-cases.json --profile demo/phase12d2/budget-control-profile.json --output work/phase12d3/reproduced-http.json --ollama-executable <本机已有Ollama可执行文件>
```

这里沿用上一阶段独立诊断配置的 40 秒调用预算，未更改系统默认 20 秒配置、模型或提示词。脚本临时启动仅本机可访问的 HTTP 服务，执行真实工具和原 Agent/Gate，保存真实状态后关闭临时服务。生成答案只读取封存 AnswerEnvelope。

使用的诊断工具名称仍为 Phase12D.2；其 `selected_has_version` 只检查原选定调查 Artifact，不检查本阶段新增的核验 `version_observations`，不能把该旧诊断字段单独当作新的交接失败。

## 全量工程回归

使用全新空的专用 `aegis_phase5_test` 数据库；不要复用演示库、正在标注的库或已有测试记录库。配置 `AEGIS_TEST_DATABASE_URL` 后运行：

```text
python demo/phase12d3/run_backend_regression.py
```

运行所有后端测试，先验证迁移和空数据契约，全部其他测试随后执行，无跳过。测试用 Mock LLM，包含现有缓存的真实 Embedding 控制；JSON/XML 输出保存到忽略目录，不携带密钥。

## 结果的含义

成功记录位于 `docs/phase12d3`。确认影响版本支持风险判断，并不证明 PyNcclPipe 已启用、端口实际暴露或利用已成功；这些运行条件没有扫描。未知、缺证据和冲突仍由原规则阻断。历史数据中无效证据、不可解析版本表达式不会被此演示自动修好。
