# Phase12D.1 本机规划稳定性与HTTP闭环复现

项目为 AegisAI / ICT命题九。这里是固定问题的运行协议检查，不是 AegisBench 正式实验。没有人工标准答案，不提供安全准确率。

`cases.json` 包含漏洞事实、PyTorch2.5.1影响、多步骤证据调查三个固定问题。数据为已有的真实来源记录，版本问题没有附带真实资产库存。模型必须保留库存和其他证据缺口，不能发明资产ID或安全结论。

`local-real-profile.json` 为本轮配置，文本模型为已安装的本机 Qwen2.5 7B。Embedding 仍是 Mock，未验证向量语义质量。JSON模式只是Provider输出方式；Model Gateway仍运行完整JSON Schema/Pydantic检查，Planner仍运行原权限、任务、参数、覆盖和DAG验证。

## 实跑方式

先在本机配置 `AEGIS_DATABASE_URL`，连接已有开发库；数据库地址和凭据只放本机。使用已有虚拟环境和Ollama，不下载新模型。

在项目根目录的PowerShell窗口执行：

```powershell
$phase12d1Settings = Get-Content -LiteralPath './demo/phase12d1/local-real-profile.json' -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
foreach ($name in $phase12d1Settings.Keys) {
    [Environment]::SetEnvironmentVariable($name, $phase12d1Settings[$name], 'Process')
}
$phase12d1Python = './backend/.venv/Scripts/python.exe'
$phase12d1Ollama = Join-Path $env:LOCALAPPDATA 'AegisAI/ollama-runtime/v0.40.3/ollama.exe'
& $phase12d1Python './backend/scripts/probe_planner_stability.py' --planner-stability --model 'aegisai-qwen25-planner:latest' --model 'aegisai-qwen35-planner:latest' --output './work/phase12d1/reproduce.json' --ollama-executable $phase12d1Ollama
```

`--planner-stability` 每模型重复20次实际 InvestigationPlannerAdapter，再独立运行三种问题各一次HTTP完整链。20次与3次的统计分母分开，未执行Runtime的规划不当作完整链失败或成功。所有重试保留，Planner最多两次尝试，无自动修复或Mock回退。原生预热后，每次Provider调用默认20秒超时，可显式传 `--planner-timeout-seconds`；超时计入失败。去掉稳定性开关可进行每模型20次完整HTTP调查，使用环境中的超时配置，耗时更长。

测试进程启动自己的临时本机HTTP端口，用随机本机认证凭据；认证值不会写入回执或仓库。每次创建不同幂等键；报告来自各次持久化Planner诊断和实际HTTP读取。退出后停止自己的临时HTTP服务，保留已存储审计。来源库会新增本阶段审计记录，不改已有情报事实、资产、人工答案或验证规则。

## 开发演示

加载本轮配置后，停掉旧配置的后端，再使用已有 `scripts/start-local-demo.ps1` 启动。旧 `start-model-demo.ps1 -Mode REAL` 仍使用历史Phase12D配置，不会自动选本轮profile。

前端仍调用已有八个调查接口。以Trace的 `model_execution.execution_mode=REAL` 和 `source=PERSISTED_PLANNER_CALL` 确认实际模式；创建响应声明不足以证明模型已经执行。Gate只把 `PASS` / `PASS_WITH_WARNINGS` 算作验收通过。`FAILED`、`REPLAN_REQUIRED`、人工复核或缺证据结果应照实显示。

结果、调用分母和当前限制以项目根目录 `PHASE_12D1_RESULT.md` 及 `docs/phase12d1/` 回执为准。该报告未完成前，此配置仍是待验收配置。
