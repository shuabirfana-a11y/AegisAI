# Phase9 Dify Integration

Status: **PARTIAL — LOCAL RUNTIME BLOCKED**。

用户明确选择本地 Dify 部署。本轮完成固定版本部署与导入资产，并实际尝试 bootstrap / workflow smoke；当前主机缺少容器运行时及 WSL，未发生 Dify→Backend 真正调用。因此 Phase9 的“Dify真正调用Backend Tool”门槛未满足，不能标为PASS。

## 运行证据

| 项目 | 实际结果 |
|---|---|
| Docker/Podman | 命令、常见系统/用户目录和卸载登记均未找到 |
| WSL | `wsl --list --verbose` exit1，stderr为未安装WSL |
| 当前提升权限 | Administrator=false |
| 两次只读DISM功能查询 | Error740，需要提升权限；功能的具体启用状态未能读取 |
| Hypervisor / RAM | HypervisorPresent=true / 16340439040 bytes |
| Bootstrap实际尝试 | BLOCKED，未创建/启动容器 |
| 实际smoke尝试 | BLOCKED，本机8088控制台不可达 |
| Dify服务启动 / Console导入 / 发布 | 均未执行成功 |
| Dify→Backend HTTP调用 | 未发生，不用后端直调替代 |
| LLM / embedding provider | 无已配置服务凭证，未执行模型 |

原始结果：`work/phase9_dify_runtime/runtime-status.local.json`、`work/phase9_dify_smoke.json`；运行环境信息：`work/phase9_dify_environment.json`。

管理员先决条件、实际启动命令、secret设置、容器/Windows loopback可达性门槛和验收命令均在 `integrations/dify/README.md`。未启用系统功能、调用UAC、修改LAN监听或重启。[微软WSL流程](https://learn.microsoft.com/en-us/windows/wsl/install)和[Docker Windows安装说明](https://docs.docker.com/desktop/setup/install/windows-install/)给出正式安装路径；per-user Docker安装也依赖可用Linux后端。

## 固定版本与配置

[Dify1.17.1正式release](https://github.com/langgenius/dify/releases/tag/1.17.1)，commit `8387590ace4a094de812b7847fc6a4c3a27cd52b`，DSL0.7.0，Graphon0.7.0；已取得官方源码快照 `work/phase9_dify_source` 并核对其 DSL 常量及 HTTP节点测试。使用官方 Compose，而非自制“类Dify服务”。应用镜像固定该release；基础镜像的可变tag和未完成digest锁定保留为复现限制。

导入文件：

- `integrations/dify/workflows/assistant-bridge.v1.yml`：Start → JSON serializer → 受保护Assistant HTTP → response验证 → End。
- `integrations/dify/workflows/get-vulnerability.v1.yml`：Start target → JSON serializer → `get_vulnerability` Tool HTTP → ToolEnvelope检查 → End。
- `integrations/dify/prompts/roles.v1.json`：Orchestrator / Investigation / Verification / QA prompt元数据；未激活模型执行。
- `integrations/dify/compose.aegis.yaml`、`gateway/default.conf`、`Bootstrap-Dify.ps1`：本机端口、独立容器数据、固定网关、随机组件密钥、版本核验、运行状态记录。
- `integrations/dify/smoke.py`：需要真实本机Dify和已发布App key；拒绝非loopback Dify地址，失败/缺配置退出非零。
- `integrations/dify/export_tool_openapi.py`：从实际Backend contracts导出READ_ONLY OpenAPI；未知结构明确失败，不凭空补Schema。

资产Bearer秘密通过 Dify **secret环境变量** `AEGIS_ASSET_TOKEN` 设置，导出DSL为空值；不能写入报告。服务端 `AEGIS_ASSET_OWNER` 管理资产范围，用户/Dify输入不能覆盖。[Dify HTTP节点文档](https://docs.dify.ai/en/use-dify/nodes/http-request)是secret和请求能力依据。

固定HTTP node只调用内部 `aegis_gateway:8080`，网关不发布主机端口，只转发具名Tool和Assistant/contract接口，后端继续验证白名单和参数。未知URL/SQL/shell不是Dify输入；Version/Asset Match/POC/Evidence不在Dify重复实现。SSRF仅允许私网域名 `aegis_gateway`；Dify HTTP自动重试关闭，Backend重试预算是唯一执行重试来源。

网关通过 `host.docker.internal:8000` 接Windows后端；Backend继续只监听127.0.0.1。这个桥接必须在Docker可用后实际测通，不默认可达，也未改成LAN监听。Code sandbox不开放网络，Agent shell容器保持未启动。模型节点未配置。

## 验证范围

`work/phase9_dify_validation.json`：**48项通过 / 0失败**，基于该release的Graphon0.7.0包，包含实际官方DSL import plan、GraphEngine实例化、Start/Code/HTTP/End Pydantic Schema、固定URL、实际HTTP JSON序列化和Bearer生成、日志脱敏、提示注入保持为数据、非法参数与HTTP/JSON失败拒绝、Evidence/门禁不确定性原样保存。未调用GraphEngine.run，不代替Dify部署或真实网络请求。

PowerShell脚本语法检查通过；实际执行bootstrap停在Docker先决条件。尚无法进行Compose合并校验、Nginx启动语法核验、Dify Console导入/发布、sandbox实际执行、真实HTTP流和LLM相关测试。不能把上述未运行项计入测试通过数。

结构化Backend响应作为 `result_json` 文本返回，调用方再解析为JSON，避免DifyCodeNode对象深度/数组长度限制。响应上限190000 UTF-8 bytes，超限失败；保留所有Evidence、Warning、Conflict和Integration Gate字段，不生成新的事实。

## 剩余验收门槛

1. 主机完成WSL/Linux Docker前提，固定Compose启动且控制台可达。
2. 固定网关→Windows loopback 后端实际可达，原鉴权和资产权限继续生效。
3. 导入/发布两份DSL，私下设置secret及各App API key。
4. 实际Tool、Fast和Deep workflow smoke返回Dify workflow_run_id和Backend trace/run ID，再对照真实Backend ToolCall记录/Evidence。
5. 需要Dify LLM辅助功能时配置真实model provider并独立测试，不能把当前桥接称为LLM编排完成。

本轮不进入Phase10。


## 2026-10-06更新

Bootstrap再次实际退出1：Docker未安装。离线语义验证重新运行48PASS/0FAIL，见work/phase9_dify_validation_final.json。Backend具名tools/assistant202已真实运行，但不算Dify成功。用户选择稍后配置生成模型。当前Assistant DSL只提交202票据，未来还需轮询最终run/trace/Evidence/Gate；现有smoke不足以单独证明完整Deep答案。DSL4000字与Backend2000字不一致列为Minor。


## 本次续作更新

当前离线51PASS。问题上限2000；smoke不会把202票据算为最终成功，会核对run/tasks/trace/证据/gate。5次真实Backend最终校验通过，但Dify没有运行，仍PARTIAL。宿主安装包按用户最新授权下载与核验。
