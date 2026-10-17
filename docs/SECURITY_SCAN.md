# 历史敏感信息扫描复核

## Phase 13-D 补充扫描

完整历史扫描首次命中 2 项：提交 `f0f23768078895dc1a11c8428c1eb17dff82179d` 的 `docs/phase13d-e2e/PROTECTED_FILES.json` 第 70、74 行。指向 `backend/app/api/openapi_contracts.py` 与 `backend/app/assets/auth.py` 的文件摘要；已从稳定基线 `59ea2a239556e70514ce19bba52141121a98d570` 的 Git blob 重新计算 SHA-256，与每条记录逐字一致。两项均为 FALSE POSITIVE。

复核数据流为已跟踪源文件 → SHA-256 → 冻结文件清单，不读取环境变量或运行凭据，没有登录/授权消费方。告警由路径包含 api/auth 与长十六进制值触发；用重新计算摘要可复现，无法演示凭据泄露影响。标准复核及反向检查确认，没有依赖未经核验的防护假设；内存、并发和越界类检查不适用。两项在真实安全影响与利用验证门禁失败。仅追加这两个准确 commit/path/rule/line 指纹，不排除目录或规则。最终复扫结果另见本轮验证记录。

提交 `818c539084dda495f360a9c18d6af8632851d919` 的冻结合成 HTTP 夹具另有 8 项告警，均为 `Source.source_key`。逐条符合 `VERIFY_TEST_` 或 `ORCH_SYNTHETIC_` 加随机 UUID 的结构；对照 `backend/tests/agents/verification/conftest.py` 和 `backend/tests/orchestration/fixtures.py`，数据来自 `uuid4().hex`，写入合成数据源标识再随公开 Evidence 响应导出，不读取凭据或用于认证。不存在可演示的凭据利用路径，8 项均为 FALSE POSITIVE。仅追加提交/路径/行号的8个精确指纹。没有排除整个夹具目录。

工具：Gitleaks v8.30.1，[官方来源](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)。本机 Windows 归档对照发布 checksums 验证；CI Linux 归档固定 SHA256，扫描完整 Git 历史，输出启用 100% redaction。

## 初始扫描

初始提交 d5bf67321fa9641d01260234c0f3c9691fed2ca3，约 28.91 MB 文本，84 个候选项对应 60 个不同 commit/path/rule/line 指纹。逐类复核后未发现 AegisAI 私密凭据：

| 类型 | 候选数 | 依据 |
|---|---:|---|
| 文件/接口 SHA256 | 7 | MANIFEST、manifest 与冻结源码基线中的校验值 |
| 合成幂等编号 | 30 | 三份固定 Mock 回执中的 ORCH 加随机 UUID；不是登录凭据 |
| 实现标识比较 | 1 | 测试代码比较 implementation_key；没有密钥值 |
| Zenodo 文件名 | 1 | 公共 files[].key 是 CVEfixes_v1.0.8.zip |
| NIST 网页公开 Mapbox 参数 | 3 | 原公开 HTML 中的 pk. 浏览器公开访问参数；不是项目私密服务 Key |
| SAMR/Google 公共链接参数 | 22 | 标准/文章访问标识；32 位链接 key 和新闻订阅链接 |
| GitHub curl 文档占位符 | 3 | YOUR_CLIENT_ID、YOUR_CLIENT_SECRET 官方示例 |
| GitHub JSON 示例临时 clone 字段 | 17 | HTML 的 code 样例属于 octocat/Hello-World 等公开示例，private=false；没有本项目账号令牌 |

复核未连接上述参数所代表的服务、未尝试使用任何第三方 token。原始匹配值与报告不提交；仅公开数量、位置指纹和判定依据。

## 例外边界

.gitleaksignore 只记录上述初始提交的 60 个准确历史指纹。没有 blanket 路径排除，没有关闭通用 API Key 规则，没有把整个 tests、docs、research 或 Mock 目录设为可信。未来提交即使改相同文件，也必须重新通过扫描。

忽略指纹复核后历史重扫为 0 个未处理告警。扫描发现新真实凭据时停止推送；先撤销/轮换凭据，再由负责人处理历史，不自动 force push、删除历史文件或重写共享仓库。发现疑似误报先核对来源，不能直接追加忽略。

## 双重检查

scripts/ci/check_repository.py 另检查 Git 索引，拒绝 .env、私钥、数据库/日志、虚拟环境、node_modules、临时 work 文件。唯一 work 例外是已冻结的纯文件哈希基线。该检查不读取或打印敏感值。配置模板 .env.example 可保留占位内容。

Gitleaks 的准确指纹忽略只适用于 Git 历史扫描；检查当前未提交文件时仍需避免把本机数据库/虚拟环境递归输入扫描器。临时导出 Git 索引进行本阶段补充扫描的副本放在忽略的 work 目录。

以上是工程扫描及复核结果，不是“绝对不存在任何敏感信息”的保证。当前仓库继续保持 private，禁止在文档或日志中输出真实模型凭据与私人资产数据。

## Phase 12-B 补充扫描

本轮新增代码阶段的暂存差异扫描为 0 个候选。更新 MANIFEST 后，差异扫描的 2 个命中分别是删除前的旧 current_openapi_sha256 与新增的当前字段；旧值与历史 MANIFEST 一致，当前值与实际导出 OpenAPI 字节的 SHA256 一致。两者都是文件校验摘要，不是 API 凭据。

历史扫描若再次命中当前摘要，仅加入经过复核的准确 commit/path/rule/line 指纹，不排除整个 MANIFEST、契约目录或规则。扫描启用完整脱敏，原始扫描报告保存在忽略的 work 目录，禁止推送发现的真实私密凭据。

完整 Git 历史扫描仅新增 1 个指纹：提交 9ccfbb8f1489a810f5034ec67d4837e0f68f67ba，MANIFEST.json 第 356 行的 current_openapi_sha256。已用该提交的 OpenAPI Git blob 重新计算 SHA256，与字段完全一致；精确指纹记录在 .gitleaksignore。新增忽略不覆盖后续提交，推送前复扫确认无未处理候选。

## Phase 12-D.3 补充扫描

完整历史扫描仅新增一个候选：提交 544e5f0b7d9936fcec82e0b23723a32ee12c7912 的 MANIFEST.json 第 411 行 current_openapi_sha256。通过同一提交的实际 OpenAPI Git blob 重新计算摘要，与该字段和命中行完全一致，因此它是文件校验值，不是凭据。只追加这一 commit/path/rule/line 的准确历史指纹，不排除目录、文件或规则；推送前再次扫描全部历史。

## Phase 14-B3 补充扫描

暂存差异命中两项，均为删除前与新增的 OpenAPI 文件校验 SHA256；已逐项与相应文件字节核对。完整历史扫描仅新增一个候选：提交 089ca470a485ed8e94daba49fe4f83733705c1d0 的 MANIFEST.json 第 451 行 current_openapi_sha256。经同提交 OpenAPI Git blob 重算完全一致，属于校验摘要。只追加该 commit/path/rule/line 准确指纹，不排除目录、文件或规则；推送前再次扫描全部历史。没有发现需提交的凭据，原始扫描输出仅保存在忽略的 work 目录。


## C9 已验证版本同步安全复核（2026-10-17）

本次暂存扫描35项、完整Git历史94个提交扫描35项，逐项定位为docs/phase14c2和phase14c5的源码文件SHA-256基线，以及交接MANIFEST的当前OpenAPI SHA-256。源码条目是受冻结校验的文件路径到64位摘要映射；可取得的原始历史文件重新计算摘要一致，OpenAPI摘要由本次实际文件字节重算一致。没有将它们解释为模型或数据库凭据。

仅登记提交3b1c31bda388523929b5549360e71e86211c110d对应准确commit/path/rule/line指纹。保留原扫描规则，不排除目录或规则；后续修改相同文件仍需重新审查。扫描全程脱敏，原始报告和逐项复核记录保留本地work目录，不上传运行数据或凭据。
