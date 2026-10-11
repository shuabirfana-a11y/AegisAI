# 当前限制与 BACKEND_GAP

GitHub公共core配额曾耗尽，历史证据在github_availability.json、attempts/与42个真实Job；配额恢复后已取得三例官方公告、README及补丁metadata。查询范围依然有限，PoC Search最多5结果、README最多3；PARTIAL不能包装成全网覆盖。

28条去重后的PoC/Patch/Version样本尚未由人类标注，第66节“人工金标准”未满足；这是正式验收PARTIAL的主要原因。PoC只做静态信息/关联核验，usability未评估；复制README、复杂语义及更多安全来源未全面覆盖。

当前只覆盖三家官方生态与明确PyPI版本。PyTorch官方公告pip包名pytorch与现有torch包标识不一致，系统保留匹配CVE的公告，却不强制把两个包合成同一身份。vLLM patched_versions='>=0.24.0'不是单一精确修复版本，保留raw_expression与未知规范值；不能把该未知值当作对0.24.0的反证。MLflow两源影响范围确有3.3.0和3.10.0的起点差异，仍待人工复核。同origin并不算两票独立证据。

BACKEND_GAP：历史VULNERABILITY_DISCOVERED没有反向补造；没有自动抽取ExploitCondition/Remediation，也没有完整通用CVE版本语义。只实现必要本机写保护，未完成企业IAM/TLS、Docker实测、生产部署/恢复、常驻队列、任务超时回收或正式前端。Phase8资产/SBOM/风险未启动。

已知1个Starlette/AnyIO弃用警告。原Phase6有限覆盖/pending保持原语义，278主体不代表全量采集。修复期间旧的PoC候选派生冲突与未知固定版本伪冲突已自动退役并保留系统审计/历史，不能冒充真实人工复核。
