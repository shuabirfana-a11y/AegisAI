# Collector 实现

| Source | 获取路径 | 原文单位 | 处理范围与恢复 |
|---|---|---|---|
| CVE_LIST | 官方 cvelistV5 Git 元数据，固定 commit 的官方 HTTPS JSON | 每个 CVE 完整 JSON | 默认 cves/2025/32xxx + 冻结真实种子 ID；commit/diff、covered_paths、pending_paths |
| OSV | PyPI 数据集 JSON；modified_id.csv 发现；之后 GET vulns/id | 完整记录 JSON；另存明确标 partial 的 CSV 前段 | 有限基线、前 1000 行、24h overlap、所有同时间 ID、pending |
| CISA_KEV | cisagov/kev-data 官方镜像完整 JSON | 整个目录，条目保存 JSON pointer | 校验 count/唯一 CVE、ETag/304、本地完整 raw、条目 hash 差量/删除、pending |

统一 HTTP 层默认 30s 读超时、最多 3 次重试、0.1s 最小请求间隔、16MiB 解码后体积限制；429 与 500/502/503/504、Timeout/NetworkError 采用 2/4/8s+jitter，可尊重不超过 60s 的 Retry-After。400 不重试，重定向不自动跟随，地址限定到冻结官方 host/repository/bucket。超时是逐次读取/连接边界，不是整个同步的硬截止时间。

Accept-Encoding=identity；服务器仍返回 gzip 时只解码一次，保留原 transport encoding/length 元数据。SHA256 对保存的完整解码后实体字节计算，不冒充压缩线上字节的摘要；原始 JSON 不重新序列化。索引前段按完整行截断，completeness=partial，绝不把前段 hash 写成完整索引 hash。

生产不读取测试 fixture。bootstrap_ids.json 只有 ID，决定请求顺序；这些 ID 的内容仍从官方重新获取。每次 raw acquisition 在语义解析之前提交。KEV 完整目录获取与逻辑条目入库分别计数，未处理条目不会伪装为完整域覆盖。

真实网络暴露并已修复：gzip 双重解码、CVE partial clone 缺失 promisor blob、OSV 完整 CSV 读取超时。CVE 保留 Git commit/diff，记录体改走同 commit 的官方 HTTPS；OSV 前段范围公开，同时保守处理水位。初始失败 SyncRun 不删除。

官方协议：[CVE List](https://github.com/CVEProject/cvelistV5)、[OSV datasets](https://google.github.io/osv.dev/data/)、[OSV get by ID](https://google.github.io/osv.dev/get-v1-vulns/)、[KEV mirror](https://github.com/cisagov/kev-data)。其他源没有接入。
