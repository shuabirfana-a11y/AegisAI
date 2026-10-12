# Phase 12-C 固定联调场景

本目录保存联调输入与配置，**没有填写标准答案**。真实来源、模型身份、传输验证是分别记录的三个维度。

## 真实来源固定输入

[real-source-case.json](real-source-case.json)：CVE-2025-32434 / torch / PyPI / 2.5.1。该漏洞已有本地来源记录，2.5.1 只是一项待判断条件；没有虚构资产 UUID、影响结论、Patch 或 POC。每次检查新建一个幂等键，题目和范围不随机。

在完整项目根目录、后端与8769代理已启动时运行：

```powershell
& './backend/.venv/Scripts/python.exe' './backend/scripts/probe_investigation_http.py' --base-url http://127.0.0.1:8769
```

检查只允许本机 HTTP 地址、不跟随重定向；通过8769代理获取本地演示授权，不导出令牌。直接连接8000时需在检查进程的本机环境安全配置 AEGIS_ASSET_TOKEN，不将值写入脚本或聊天。

结果默认写入已忽略的 `work/phase12c/live-http-report.json`，仅保存ID、状态、计数和Schema验证摘要。退出码0表示该请求期望的模型模式与完整链都通过；1表示实际未就绪；2表示网络、配置或Schema检查失败。

**当前实际退出码1：服务仍用默认Mock，身份不符合REAL，规划状态PLANNING_FAILED，三个Agent和Gate均未产生。** 即使使用 `--mode MOCK`，也只是改变检查预期，不会切服务供应商、注入规划回执或伪造成功。

轮询预算默认45秒，可用 `--timeout` 调整至不超过120秒；单次HTTP请求限时5秒。达到检查预算后返回PROBE_POLL_TIMEOUT，不把任务当终态，不自动取消用户调查。这个检查工具不用于公网发布或模型质量评测。

## 受控完整链

[controlled-chain-scenario.json](controlled-chain-scenario.json) 固定 vLLM0.6.0 条件，复用现有 scenario(mode='complete')，只在专用测试数据库运行。合成CVE/UUID/包标识为避免重复测试相互污染而唯一绑定；不是随机抽题，不进入真实采集库。

`backend/tests/investigation_api/test_tcp_chain.py` 启动临时本机TCP端口，真实执行现有Orchestrator / Planner验证 / 三Agent / Tool Gateway / Gate / Answer。默认Mock没有规划能力，因此成功场景**显式注入合成PlannerPlan回执**，并标记SYNTHETIC_TEST；不向开发服务添加万能离线模型或预生成Agent结果。

测试还调用未改动的现有 TypeScript Client，检查八操作、冻结答案、模型模式不匹配、默认Mock失败、未授权、404、检查超时和运行中取消。使用已有本机专用测试库及环境配置后，在backend目录运行：

```powershell
python -m pytest tests/investigation_api/test_tcp_chain.py tests/investigation_api/test_live_chain.py -q
```

AEGIS_TEST_DATABASE_URL 必须由本机环境设置，数据库名只能为 aegis_phase5_test；未配置时测试明确失败，不静默跳过。这里是工程联调，不是正式AegisBench。

## 模型配置准备

[model-profiles.json](model-profiles.json) 提供三个不含Key的配置样例：MOCK、REMOTE_COMPATIBLE、LOCAL_COMPATIBLE。它**不会自动加载**。

- 远程或国产模型仅在供应商支持现有OpenAI兼容协议时使用openai_compatible；替换占位MODEL_NAME和HTTPS MODEL_API_BASE，Key仅配后端环境。
- 本地模型需要用户实际运行兼容服务；样例11434端口与local-served-model不表示当前已经安装/提供模型。本轮没有下载或启动模型。
- structured_mode默认prompt_json；json_object/json_schema应按具体供应商能力选择，不能只因配置Schema接受就宣称供应商支持。
- 样例独立Embedding仍为Mock；旧Hybrid Retrieval调用点不迁移。切换文本模型不是整个检索/模型链真实化。
- 配好后重启已授权的后端进程，再用固定输入检查实际is_mock和执行链；不更改Planner/Runtime/Agent/Gate。

本阶段只离线验证三组ModelConfig配置合法，没有真实模型调用、效果比较、Ground Truth填写或公网部署。当前结论见项目根目录PHASE_12C_RESULT.md。
