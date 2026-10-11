# 真实来源与演示库存案例

所有资产is_demo=true，为本地配置，未扫描或声称发现用户生产部署。

Case1：手工PyTorch2.5.1，匹配已有CVE-2025-32434及同包真实漏洞；范围含unsupported/未确认陈述，最终UNCERTAIN。case_1.json保存实际POST/GET数据。
Case2：CycloneDX1.6 MLflow3.14.0+torch2.6.0+vllm0.8.2-custom；3组件真实导入，重复导入added0/updated0/removed0；所有未知保留。case_2.json。
Case3：同库存MLflow3.14.0→3.15.0，revision增加、技术比较AFFECTED→NOT_AFFECTED、产生版本/情报变化，但范围冲突使最终UNCERTAIN→UNCERTAIN，没有伪造风险完全解除。case_3.json、sbom_update_actual.json。

补充：SPDX2.3实际导入torch2.6.0（spdx_actual.json）。Demo Candidate为MLflow/CVE-2026-64849，能展示KEV/EPSS/official fixed3.15.0/Patch/Evidence与不确定性；完整确定性升级解除真实案例受前阶段冲突/核验覆盖限制。
