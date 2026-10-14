# 发布前检查

实现暂存扫描零发现；结果初扫 95 个 generic-api-key 命中均经核验为 bench-UUID 幂等标识、CVSS scope SHA256、Evidence locator SHA256 或受保护文件 SHA256。locator 和文件摘要重新计算比对，原始结果未删改。

精确位置见 secrets-scan-identifiers.json。只对对应 commit/file/line/rule fingerprint 登记，没有关闭规则或排除整个目录。登记后全 Git 历史扫描零未处理发现；Repository safety 和空白检查通过。

独立比对本轮私有认证 Token，所有暂存文件和交付包均不含该值。没有上传模型 Key、数据库连接配置、私有 Token 或服务日志；这些仍留在 work/ 的本机配置中。

命令为 `gitleaks git . --staged --redact`、`gitleaks git . --redact --log-opts="--all --full-history"`、`python scripts/ci/check_repository.py` 和 `git -c core.whitespace=cr-at-eol diff --cached --check`。日志/扫描报告保存在私有工作目录，发布结果只记录位置与非凭据分类。
