# 发布安全检查

导入49份签核原件的暂存扫描零发现。实验结果初扫440个generic-api-key命中均逐位置核验为bench随机幂等标识、领域scope标识、Evidence locator摘要或文件摘要；没有删改原始实验记录。

幂等标识符合bench-32hex；scope字段为SHA256或公开生态/公告标识；locator摘要从原locator重新计算；PROTECTED_HASHES中的摘要与真实文件字节复算一致。所有暂存文件逐一比对本轮私有认证Token，均不含该值。

精确文件、行和规则见 `secrets-scan-identifiers.json`。只登记对应提交/file/line/rule的440个fingerprint，没有排除目录、关闭规则或加入通用匹配例外。登记后的全Git历史扫描需为零未处理发现才推送。

模型API Key、数据库连接配置、私有认证Token及服务日志未导出。交付包将再次对私有Token字节检查。运行环境配置只保留原无密钥的本机Provider参数。

本次命令：`gitleaks git . --staged --redact`、`gitleaks git . --redact --log-opts="--all --full-history"`、`python scripts/ci/check_repository.py`、`git -c core.whitespace=cr-at-eol diff --cached --check`。扫描日志只保存在本机忽略目录，不上传日志或凭据值。
