# Phase12D 密钥扫描候选复核

工具Gitleaks v8.30.1，暂存差异扫描，100%脱敏。候选1：`AegisAI_FRONTEND_HANDOFF_PACKAGE/MANIFEST.json:401`，规则generic-api-key。

**FALSE POSITIVE：暂存命中值为current_openapi_sha256，精确等于包内生成OpenAPI文件的SHA-256，不是认证凭据。随后历史扫描另外命中3处合成请求编号生成表达式，已逐项核对。真实密钥发现0，误报共4处。**

## 来源与用途

声明的风险：提交了可用于访问服务的API Key。实际流向：公开API Schema字节 → hashlib.sha256 → MANIFEST完整性元数据。执行字节哈希比较通过，401行是current_openapi_sha256字段。这个值由文件内容确定，任何包接收者均可重算。

检索backend/app、frontend、scripts及工程测试没有发现current_openapi_sha256被用作认证输入。应用访问令牌来自进程环境，模型API Key来自独立ModelConfig；二者不是该文件摘要。没有尝试用扫描值访问任何服务。

## 标准验证

- 可达/控制：仓库阅读者可以读公开摘要，但没有把它送入认证比较的代码路径。
- 影响：没有本项目私密凭据泄露证据；只发现API字段名与高熵摘要触发了规则。
- 复现：读取MANIFEST字段，计算api/reference/openapi.json的SHA-256并比较；相等。认证利用路径无法复现。
- 反向核查：摘要原则上可被人为拿来当密码，但当前项目没有这种赋值或消费者，不能凭假设判定泄漏；没有把扫描器本身或脱敏当作安全控制。
- 六门核查：流程证据充分；可达漏洞、真实影响、利用路径未通过；数学检查证明命中为文件摘要，环境认证与它独立。适用信息泄漏检查未找到跨边界秘密源。
- 误报模式13项已核对：关键反例为数据用途并非认证、缺少危险消费者、根据命名模式误判；内存边界/竞态/整数项不适用于文件摘要发现。

保留扫描告警数量和复核依据。Git历史只加入本次具体commit/path/rule/line指纹例外，不忽略整个目录、文件或规则。原始扫描日志留在本机忽略目录，不提交匹配的任何疑似秘密原文。

## 历史提交的三个候选

| 提交 / 文件 / 行 | 实际来源 |
|---|---|
| 61b1155 / backend/scripts/probe_model_provider.py / 158 | 合成探测idempotency_key前缀拼接uuid4().hex |
| 61b1155 / 同文件 / 164 | 合成探测request_key前缀拼接uuid4().hex |
| 83e753c / backend/tests/investigation_api/test_model_execution.py / 35 | SYNTHETIC测试request_key前缀拼接uuid4().hex |

三项从具体commit的原始文件逐行核对：命中的是编号生成代码表达式，不是保存的凭据。它们流向幂等/去重字段，不流向Authorization；Orchestrator按owner、request_key和请求哈希复用记录，身份仍来自独立环境令牌比较。攻击者可选自己的幂等编号，不因此获得其他owner的数据。没有联系任何外部认证服务。

同样完成来源、消费者、影响、利用路径、反向检查及六门核查：不存在这三个编号被用作认证的路径，信息泄漏真实影响无法成立；均为FALSE POSITIVE。只登记上述原始提交的精确指纹。
