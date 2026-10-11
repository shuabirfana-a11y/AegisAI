【第一批实现】

Source 1：CVE Program / cvelistV5（CVE_LIST）
用途：权威CVE身份、状态、CNA原始描述/影响/引用，同时保存Program和ADP容器。
获取方式：官方Git仓库一次基线，之后按commit差异同步；release baseline/hourly delta为断点恢复备选。
选择原因：官方明确推荐Git持续更新；本轮真实JSON成功；直接处理撤销与上游原文，无需CNA账号。NVD留给CPE/评分补充。

Source 2：OSV.dev（OSV）
用途：开源Package/生态/受影响版本事件、明确fixed、GHSA/PYSEC等别名。
获取方式：首次限定PyPI官方Dataset；后续读取官方PyPI modified_id.csv取变化ID，GET /v1/vulns/{id}；按需POST /v1/query只作查询。
选择原因：原生版本事件最适合当前AI Python组件；增量索引有官方文档且真实CSV已取样。直接接GHSA会大量重复，先保留lineage。

Source 3：CISA KEV（CISA_KEV）
用途：某CVE已被收录为已知利用的正证据、处置建议/加入日期。
获取方式：CISA官方GitHub镜像的JSON，ETag条件获取，变化后对目录计算差异。
选择原因：与CVSS严重度/EPSS概率职责不同；官方镜像和CC0文本已验证；完整小目录便于校验count与撤销。没有变化不下载。

【第二批实现】

1. 厂商公告：先PyTorch、vLLM、MLflow三个官方repo的已发布advisory；按明确引用取GitHub元数据。补修复建议、版本与POC线索。全部公开API已取真实样本；不访问未公开公告。
2. arXiv：官方Atom API，先元数据/摘要与版本；关联论文是候选，不能把相似摘要当确证。
3. 安全研究文章：Trail of Bits官方RSS + Google Security Blog官方链接的HTTPS Atom。先元数据/链接，正文留存/再分发按许可范围；覆盖无CVE事件。
4. 技术标准与政策：国家标准信息平台（先GB 45438-2025）+ NIST AI规范/出版物目录 + 中国网信办官方栏目。正式标准、指导框架和政策类型分开。论文、标准、政策均是M1必做，这些接入必须在完整初赛验收前完成。
5. FIRST EPSS：已监测CVE少量API查分；需要全量时按官方当前文档每日CSV。每个分数保存日期/model_version；不把概率等同已利用。
6. GitHub引用富化：有限repo与reference路径，API读Issue/PR/commit/release，完整SHA和适用分支留证；M1服务PoC线索，M2再扩Patch。不建设复杂全站搜索。
7. CISA Vulnrichment：首批已有CVE CISA-ADP原文先解析；仅需独立更新/缺口时同步官方Git库。避免重复下载相同ADP，SSVC版本/时间与原始判断并存。
8. MITRE ATLAS + OWASP GenAI：官方版本化知识，保留原许可/署名、ID及版本，不当实时攻击遥测。

【暂缓】

NVD独立接入：API真响应已确认，但本轮开发/许可页为JS壳；重新确认限额/窗口后补CPE/评分，首批不依赖。
GHSA独立全库：OSV已涵盖大量相同GHSA；出现实际差异/时效缺口再接，不以入口数增加可信度。
其余厂商：TensorFlow、NVIDIA/Triton、Ollama、Hugging Face、LangChain、LlamaIndex、Ray、Jupyter、AI相关Kubernetes均已查官方入口；有限开发预算先做三个，空advisory返回不等于无漏洞。NVIDIA机器接口尚未确认。
EUR-Lex：本轮官方正文与许可页202空响应，不能称可自动采集；首期政策由中国官方源承担，后续合法接口明确后再接。
CycloneDX/SPDX/OpenVEX/CPE解析器：只研究规范并保留源表达；PURL身份先采用，其余在授权SBOM/适用性需求出现后实现。它们不是额外漏洞情报源。
大型CTI平台：不直接Fork、改皮或复制GPL/AGPL/商业许可代码；只学习适配器/调度/溯源模式。

# 冻结说明

第一批恰好3个源，覆盖身份、Package/Version与利用风险；只是M0基础切片，不能当完整初赛、三个业务类别或已完成POC/Agent。CISA ADP是在已有CVE原文中保留的容器，不额外算第四个采集源。

首期包范围为PyPI，AI产品从既有torch、vllm、transformers、gradio、mlflow、ray样本起步；不是最终覆盖全部AI产品。CVE遍历范围与历史回补登记清楚，未覆盖范围不能对外声称不存在漏洞。KEV必须取完整目录后才能说“未在该次目录收录”，这仍不证明未被利用。Demo允许CVE-2025-32434历史回放与真实KEV解析对照；若AI白名单当前无KEV命中，展示真实空结果，不伪造命中。

Tier 1三源；Tier 2是上述有限第二批（17个采用入口合计，GitHub工具入口与厂商共享平台但独立用途）；Tier 3仅按缺口扩展。全部运行配置enabled=false、last_success_at=null，防止把本阶段HTTP可行性probe当已部署采集。

许可UNKNOWN不解释成自由使用：采用仅限对应acquisition_mode；未经确认不公开分发全文/数据集。官方数据源许可与代码许可分别核对；EPSS旧代码MIT不能代替分数数据授权。详情见候选表及安全要求。

12项完成检查见validation.json；所有未知项和接入前复核项仍显式保存。完成本阶段后停止，下一阶段建议：UX与核心业务流程设计。
