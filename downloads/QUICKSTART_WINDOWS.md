# Windows 本地启动

## 1. 前置条件

- Windows PowerShell 7；Python 3.12；Node.js 22 或更新的兼容版本；Git。
- PostgreSQL 17，以及一个由你创建的专用数据库和具有建表权限的本地账号。
- 能生成结构化计划的真实模型服务。支持现有 OpenAI 兼容协议；本地 Ollama 兼容入口通常为 `http://127.0.0.1:11434/v1`。模型服务、权重及许可需要自行准备，不在仓库中。
- 网络采集需要能访问所配置的公开数据源。下载模型和依赖需要网络与足够磁盘；模型运行资源按所选模型确定。

在克隆后的仓库根目录操作；不要使用他人的数据库密码或调查资产 UUID。

## 2. 安装依赖

```powershell
py -3.12 -m venv backend/.venv
& ./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Push-Location frontend
npm ci
Pop-Location
```

后端依赖以现有 requirements.txt 为准。`npm ci` 安装锁定开发依赖，前端运行本身使用 Node 内置 HTTP 与浏览器模块。

## 3. 配置数据库与模型

先在 PostgreSQL 中创建专用空数据库，例如 `aegis_demo`。示例账号必须由本机管理员创建并授权。把 `backend/.env.example` 作为字段说明，应用不会自动加载这个文件；在启动后端的同一终端设置环境变量：

```powershell
$env:AEGIS_DATABASE_URL = 'postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@127.0.0.1:5432/aegis_demo'
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
$env:AEGIS_GIT_BIN = (Get-Command git).Source
$env:AEGIS_ASSET_TOKEN = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant()
$env:AEGIS_ASSET_OWNER = 'local-analyst'

$env:MODEL_PROVIDER = 'openai_compatible'
$env:MODEL_API_BASE = 'http://127.0.0.1:11434/v1'
$env:MODEL_NAME = 'YOUR_ACTUALLY_SERVED_MODEL'
$env:MODEL_ALLOW_KEYLESS_LOCAL = 'true'
$env:MODEL_STRUCTURED_MODE = 'prompt_json'
$env:MODEL_TIMEOUT_SECONDS = '60'
$env:MODEL_MAX_OUTPUT_TOKENS = '4096'
$env:MODEL_EMBEDDING_PROVIDER = 'mock'
$env:MODEL_EMBEDDING_NAME = 'mock-embedding-v1'
$env:MODEL_EMBEDDING_DIMENSION = '384'
```

替换上面的数据库占位和实际模型名称，不要把凭证保存到 Git。使用远程服务时改为供应商 HTTPS 地址，在进程环境安全设置 `MODEL_API_KEY`，不要启用本地免密选项。这里的 mock embedding 仅用于复用已有检索配置，不表示检索已切换为真实向量模型；也不会替代真实文本模型生成。

本地真实模型的历史演示配置为 `aegisai-qwen25-planner:latest`，但这一名称属于演示机本地模型，不会随代码自动出现。没有该模型时，应先准备实际可用模型，再明确记录配置差异，不宣称复现原实验分数。

## 4. 初始化和启动后端

```powershell
& ./backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
& ./backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

迁移仅针对你设置的专用数据库。不要指向唯一备份、评测库或现有生产库。接口文档为 `http://127.0.0.1:8000/docs`，健康检查为 `/health`。健康通过后仍须检查模型和来源数据。

需要首次获取少量公开漏洞资料时，在另一个已设置相同数据库环境的终端显式运行：

```powershell
& ./backend/.venv/Scripts/python.exe -m app.cli sync --source OSV --limit 10
```

采集是有边界的真实网络操作，结果可能为 PARTIAL 或失败，不能假定已经具备指定公告或所有数据。资产相关接口使用本机登记库存；新数据库没有演示机的资产和历史调查。SBOM/资产管理员操作见 `backend/README.md`，不要把私有数据库 dump 当作公开初始化数据。

## 5. 启动现有前端

另开仓库根目录终端：

```powershell
node frontend/server.mjs
```

打开 `http://127.0.0.1:8769/assistant`。此入口固定代理到 `127.0.0.1:8000`。在本机页面密码字段填写本次后端的访问令牌，令牌只在浏览器会话内使用，不写入仓库。选择“真实 API”，不要用 Mock 页面结果冒充实时调查。

若后端运行于其他端口，应使用已经核实的现有包装配置；不要直接套用默认端口。历史演示机的 8066/8770 是另一套本机运行实例，不是新机器默认入口。

## 6. 查询与停止

- 在工作台提交合法问题后，查看调查 ID、进度、Trace、Artifact、Gate 和答案引用。
- 缺版本时预期请求补充；证据不足或冲突时应保留未知或人工复核。
- 前后端在各自终端按 Ctrl+C 停止。数据库用自己的 PostgreSQL 管理方式停止。
- `scripts/start-local-demo.ps1` / `stop-local-demo.ps1` 是历史便携开发库启动器，依赖开发机 PostgreSQL 缓存，不是新机器通用安装器。`start-model-demo.ps1` 也沿用该启动器，不应直接替代以上步骤。

## 常见问题

|现象|检查|
|---|---|
|数据库健康失败|数据库正在运行、URL与端口正确、账号权限和迁移已准备|
|401/503|本机 AEGIS_ASSET_TOKEN 已设置，页面使用同一令牌；不要关闭鉴权|
|PLANNING_FAILED|实际模型已加载且支持当前结构化输出；默认 Mock 不提供任意计划|
|502 或连接超时|后端是否为 8000、前端代理端口是否匹配；保留错误日志|
|没有漏洞/资产|新数据库为空；按许可显式采集或登记数据，不能复用别人的 UUID|
|Worker 创建失败|保留原错误、操作系统和调用栈；Windows 组合运行问题尚未解决，不绕过安全阻断|
|DOM 测试找不到 jsdom|在 frontend 目录按锁文件执行 npm ci|

本次发布检查不等于在全新 Windows 机器完成冷启动验收；实际模型能力、网络来源和资源仍由运行环境决定。
