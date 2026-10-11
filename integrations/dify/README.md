# AegisAI 本地 Dify 接入

本轮状态为 **PARTIAL / RUNTIME BLOCKED**。两份 DSL 已用 Dify 1.17.1 的实际 `graphon==0.7.0` 依赖通过离线语义检查，但本机没有 Docker/Podman，WSL 未安装，当前会话没有管理员权限。因此没有启动 Dify、没有在 Dify 导入/发布应用，也没有发生 Dify→Backend 的真实请求。不能把后端直接调用或离线 GraphEngine 实例化计为 Dify 验收。

## 版本与文件

- Dify release：`1.17.1`；commit：`8387590ace4a094de812b7847fc6a4c3a27cd52b`。
- DSL：`0.7.0`，以该 release 的 `api/constants/dsl_version.py` 为准。
- 工作流：`workflows/assistant-bridge.v1.yml`、`workflows/get-vulnerability.v1.yml`。
- 部署：`Bootstrap-Dify.ps1`、`compose.aegis.yaml`、`gateway/default.conf`。
- 配置模板：`deployment.env.example`；实际凭证不填写进此文件或 DSL。
- 离线校验：`validate_dsl.py`；实际 API 验收：`smoke.py`。
- 可选工具 Schema 导出：`export_tool_openapi.py`，只导出后端已经登记的 READ_ONLY 工具。
- 可选模型角色 Prompt：`prompts/roles.v1.json`；当前未激活。

[官方固定 release](https://github.com/langgenius/dify/releases/tag/1.17.1)和[Docker Compose 部署说明](https://docs.dify.ai/en/self-host/deploy/quick-start/docker-compose)是版本与部署依据。Dify 的应用镜像固定为1.17.1；官方基础镜像中仍有可变 tag，首次成功拉取后应保存各镜像 RepoDigest，不能声称已经完成镜像 digest 锁定。

## 本机先决条件

已实际检查：`wsl --list --verbose` 退出1，stderr 显示 WSL 尚未安装；Docker/Podman 命令和常见系统/用户安装目录均未找到；当前进程 `IsInRole(Administrator)=false`；两次只读 DISM 功能检查返回740（需要提升权限）。系统报告 HypervisorPresent=true、约16GiB RAM，未尝试启用系统功能、调用 UAC 或重启。

管理员在独立 PowerShell 中安装 WSL，按系统提示完成重启：

```powershell
wsl --install
wsl --list --verbose
```

这是[微软安装流程](https://learn.microsoft.com/en-us/windows/wsl/install)。具体可选功能当前状态无法在本会话读取，重启是否必要以安装结果为准。

再安装并启动 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)，选择 Linux 容器及 WSL2。官方目前支持无需管理员安装的 per-user 模式，但它不能替代未安装的 WSL 前提。安装器由操作者从官方页面取得；本脚本不会下载/运行 OS 安装器或自动接受协议。已取得官方安装器后，per-user 命令为：

```powershell
Start-Process -FilePath '.\Docker Desktop Installer.exe' -ArgumentList 'install','--user' -Wait -WindowStyle Hidden
docker info
docker compose version
```

这里至少要求 Compose2.24.4，覆盖 `!override` 的支持。建议为 Docker 留出2CPU/8GiB内存并按官方建议将 Linux 绑定数据保存在 Linux 文件系统；本项目的 Windows 默认运行目录便于本地验证，性能未量测。

## 启动与接线

在项目根目录运行：

```powershell
& './integrations/dify/Bootstrap-Dify.ps1' -RuntimeDirectory './work/phase9_dify_runtime'
```

脚本验证 Linux Docker 引擎与 Compose 版本，克隆固定 release 并核对完整 commit，再把覆盖配置和网关配置复制到官方 `docker/` 下。它只在首次创建 `.env` 时生成组件随机密钥，已有 `.env` 保留。控制台只绑定 `127.0.0.1:8088`；插件调试端口只绑定本机；网关没有宿主机端口；Agent shell 容器不启动，Code sandbox 关闭网络。Dify 的数据库与 pgvector 均为自己的容器，不能接入 AegisAI PostgreSQL。

浏览器打开 `http://127.0.0.1:8088/install` 完成本地管理员初始化。导入两份 DSL，分别在 app 的环境变量中将 `AEGIS_ASSET_TOKEN` 配置为 **secret**，与 Backend 运行时 Bearer 凭证一致，再发布 app。该变量的导出值为空，不包含凭证。[Dify HTTP Request 文档](https://docs.dify.ai/en/use-dify/nodes/http-request)说明了 secret 环境变量和请求配置。

固定网络路径为：

```text
Dify HTTP node
  → http://aegis_gateway:8080/api/v1/assistant/query
    或 /api/v1/tools/get_vulnerability
  → http://host.docker.internal:8000
  → Windows AegisAI Backend (127.0.0.1:8000)
```

网关只转发 Assistant query、Tool contracts 和具名 Tool POST；未知工具仍由 Backend 的白名单拒绝。用户输入没有 URL、SQL 或 shell 参数；服务端 `AEGIS_ASSET_OWNER` 决定资产所有权，Dify `user` 参数不能修改它。代理保留 Backend 的 Bearer 鉴权，禁用访问日志以减少凭证/问题暴露。

**必须实际测试容器到 Windows loopback 的可达性。** [Docker Desktop 提供 `host.docker.internal`](https://docs.docker.com/desktop/features/networking/)，但不同后端/防火墙配置不能保证只监听127.0.0.1的服务能通过内部宿主地址访问。可先在已经启动的网关容器请求固定 contracts 路径；Backend401代表已抵达后端，502/连接拒绝代表桥接仍未完成。不要为省事把 Backend 改成 `0.0.0.0` 或打开 LAN 防火墙端口。本轮没有创建隧道或 LAN listener。若实际检查失败，需要另行实现并验收仅限 Docker 私有接口的转发，或把 Backend 移至可共享的隔离容器网络；这项工作不能默认已完成。

官方 Compose 的私网 SSRF 例外仅放行 `aegis_gateway`，没有开放整个私网网段。HTTP node URL 写死，秘密只用于 Authorization，HTTP node 不自动重试；由 Backend 的 Task/Tool retry 策略负责重试，避免重复副作用。

## 实际验收

从各已发布 app 的 API access 页取得 app key，私下放到当前进程环境变量中，Assistant 使用 `DIFY_APP_API_KEY`，工具工作流使用 `DIFY_TOOL_APP_API_KEY`。不要把 key 放进命令历史、README或交付记录。`DIFY_API_URL` 默认本机8088；smoke拒绝非loopback地址。

```powershell
& './backend/.venv/Scripts/python.exe' './integrations/dify/smoke.py' --kind tool --output './work/phase9_dify_tool_smoke.json'
& './backend/.venv/Scripts/python.exe' './integrations/dify/smoke.py' --mode fast --output './work/phase9_dify_fast_smoke.json'
& './backend/.venv/Scripts/python.exe' './integrations/dify/smoke.py' --mode deep --question '调查 CVE-2026-64849 的可靠 POC、已知利用和修复，并说明证据冲突。' --output './work/phase9_dify_deep_smoke.json'
```

工具工作流须输出 `PASS_REAL_DIFY_HTTP_BRIDGE`。Assistant 工作流须输出 `PASS_REAL_DIFY_ASSISTANT_FINAL`：脚本先核对真实 Dify workflow_run_id 和202票据，然后使用本机环境变量 `AEGIS_ASSET_TOKEN`，从固定的本机 Backend 地址轮询该 run（最多150秒），读取最终 tasks/trace，检查任务与 trace 绑定、来源证据在工具审计中的一致性、确认事实的证据及 integration gate。只有202提交成功不会通过 Assistant 验收。

`AEGIS_API_URL` 默认 `http://127.0.0.1:8000/api/v1`，只允许loopback及固定路径，不接受票据提供的URL，携带凭证的请求不跟随重定向。Dify应用中的secret须与脚本和Backend的token一致；不同owner无法读取运行。`WAITING_REVIEW`、冲突和 Unknown 原样保留，输出 gate_status 为 `HUMAN_REVIEW_REQUIRED`；“完成接入验收”不代表“安全结论已通过门禁”。DSL仍返回票据，最终轮询由验收脚本/前端完成。

DSL 的 `result_json` 是完整 Backend JSON 文本，调用方解析一次即可得到结构化响应；这避免了 Dify CodeNode 对对象深度/数组长度的限制。结果预算190000 UTF-8 bytes，超出时 workflow失败，不能截断证据后当作成功。

## 离线核验与模型限制

在独立验证环境安装 `validation-requirements.txt` 后执行：

```powershell
python './integrations/dify/validate_dsl.py' --output './work/phase9_dify_validation.json'
```

本次实际命令使用已有 Python3.12，仅将验证依赖安装在 `work/phase9_dify_validation_lib`，没有修改 Backend 依赖：

```powershell
& './backend/.venv/Scripts/python.exe' './integrations/dify/validate_dsl.py' --library-path './work/phase9_dify_validation_lib' --output './work/phase9_dify_validation.json'
```

本轮结果：51项通过、0失败，含官方 parser/graph/node schema、实际 HTTP 请求 JSON/auth 日志处理、输入注入保持为数据、非法target/参数和非法后端响应拒绝。新增2000字边界保留、2001字拒绝、UI限长与Backend一致。这个结果不代替 Dify部署、Console导入、sandbox执行或真实网络集成。

本机没有已配置的 Dify LLM provider/embedding key，因此两份可执行 DSL 是 **model-free HTTP bridge**。Dify还没有执行模型辅助任务理解、LLM规划、Agent节点或模型切换；角色Prompt是版本管理的配置资产。没有把假模型、mock endpoint或离线 Graphon运行包装成 Dify。后端确定性 Agent角色实现与 Dify模型辅助能力应分别汇报。

## 许可

Dify使用带附加条件的Apache2.0修改版，保留原Console品牌/版权；这是单工作区本地部署配置。[该版本原始 LICENSE](https://github.com/langgenius/dify/blob/1.17.1/LICENSE)已保存于 `vendor-notices/DIFY-LICENSE`。Graphon为Apache2.0，验证库wheel的原许可已保存于 `vendor-notices/GRAPHON-LICENSE`。正式多租户或品牌更改须按原许可另行处理，本轮未涉及。
