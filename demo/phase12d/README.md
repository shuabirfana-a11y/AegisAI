# Phase 12-D 本地模型配置

2026-10-12：本地免费模型已经安装，Gateway 的健康、文本和小型 JSON 调用通过。**真实调查仍未就绪：默认配置两种 Planner 输入均被原验证器拒绝。** 服务可启动、JSON 合法、完整调查成功是三个不同的检查。

## 文件

- `mock-profile.json`：CI/开发配置，文本与 Embedding 都为 Mock。默认 Mock 没有 PlannerPlan 成功 fixture，不能承诺生成完整调查。
- `local-real-profile.json`：Ollama 本机 Compatible Provider，模型 `aegisai-qwen25-planner:latest`，文本为 REAL、Embedding 仍为 Mock。
- `Modelfile`：Qwen2.5 7B Q4_K_M，16K 上下文；不下载 embedding、不迁移旧检索调用。

## Windows 准备

在项目根目录使用 PowerShell 7；先准备项目 Python 环境。模型原生运行在 Windows，不需要 WSL、Linux 或 Docker。

```powershell
.\scripts\setup-local-model.ps1
```

脚本使用官方 Ollama v0.40.3 Windows zip，固定大小及 SHA-256，保留可续传下载。运行时和模型保存在 `%LOCALAPPDATA%\AegisAI`，不会提交 Git。模型服务仅监听 `127.0.0.1:11434`，设置 `OLLAMA_NO_CLOUD=1`。已占用端口会直接拒绝操作，不替换已有服务。

已有本阶段启动的服务时可继续使用。安装脚本重复执行会报 `MODEL_PORT_ALREADY_OCCUPIED_NO_CHANGES`，这是保护已有服务；勿关闭其他人的进程。模型首次加载可能超过60秒，先在自己的终端使用已安装的 Ollama 空输入预热：

```powershell
$modelExe = Join-Path $env:LOCALAPPDATA 'AegisAI\ollama-runtime\v0.40.3\ollama.exe'
'' | & $modelExe run aegisai-qwen25-planner:latest --keepalive 30m
```

空输入仅预加载模型，不生成安全结论。项目正式模型请求仍全部通过 Model Gateway，单请求配置最高60秒；探测器另外给自有子进程设180秒上限。

## 明确切换模式

```powershell
.\scripts\start-model-demo.ps1 -Mode MOCK -PythonPath '你的项目Python环境\Scripts\python.exe'
.\scripts\start-model-demo.ps1 -Mode REAL -PythonPath '你的项目Python环境\Scripts\python.exe'
```

两条命令选择一种执行。已有8000/8769服务时会拒绝重复启动。包装脚本只临时改变子进程模型配置，结束后恢复调用终端环境；不会写用户级/系统级变量。前端启动异常会清理本次已启动的后端。现有数据库启动器需要本机 `work/postgresql_runtime.json`、PostgreSQL运行时和已授权迁移环境；这些模型脚本不是新电脑数据库安装器。

真实模式当前仍可能返回 `PLANNING_FAILED`。服务启动输出只确认 HTTP 可达，不表示调查成功。

## 单独检查 Provider

```powershell
$profile = Get-Content .\demo\phase12d\local-real-profile.json -Raw | ConvertFrom-Json -AsHashtable
foreach ($entry in $profile.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($entry.Key, [string]$entry.Value, 'Process')
}
& '你的项目Python环境\Scripts\python.exe' backend/scripts/probe_model_provider.py --mode REAL
```

在独立终端执行这段配置，退出终端即结束其作用。输出在忽略的 `work/phase12d/provider-report.json`。退出0表示所有固定检查通过，1表示检查未全部通过，2表示参数/配置失败，130表示用户中断。中断会标记报告失败并清理探测器自己的工作进程，避免保留旧的 `ready=true`。

## 扩展配置

现有配置：`MODEL_PROVIDER`、`MODEL_NAME`、`MODEL_API_BASE`、`MODEL_API_KEY`、`MODEL_ALLOW_KEYLESS_LOCAL`、`MODEL_TIMEOUT_SECONDS`、`MODEL_MAX_OUTPUT_TOKENS`、`MODEL_STRUCTURED_MODE`、`MODEL_TOKEN_PARAMETER`。Embedding 单独配置。

新增可选 `MODEL_REASONING_EFFORT=none|low|medium|high`，为空或未设置时不改变供应商默认行为。只在支持它的服务上配置；本轮 Qwen3.5 兼容检查使用 `none`，结果见 [实际记录](../../docs/MODEL_PROVIDER_TEST.md)。不向前端传 API Key、模型服务地址或私有输出。

本轮没有配置收费 API。兼容云模型仍需自己配置真实凭据；不会在本地模型失败时自动切云或切 Mock。

官方参考：[Windows 原生安装](https://docs.ollama.com/windows)、[Qwen2.5 固定模型](https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M)、[OpenAI兼容接口及思考配置](https://docs.ollama.com/api/openai-compatibility)。
