# AI 相关性 V0

人工维护 resources/ai_products.json，版本 ai-registry-v0.1。精确注册 PyPI 包或审查过的产品别名才返回 relevant；只有 AI 关键词返回 uncertain；明确产品/包未命中注册表或上下文，返回可修订的 irrelevant；身份不足为 uncertain。结果以 AiRelevanceAssessment 追加保存，含规则方法、注册表版本、原因与 observation。

注册产品：PyTorch、vLLM、TensorFlow、Transformers、Hugging Face Hub、LangChain、LlamaIndex、Ray、MLflow、Gradio、Ollama Python client、triton-lang。包名使用 PEP503 规范化；PyTorch 与显式 PyPI torch 可对应。Ray/Ollama/Triton 等歧义非限定名称不会自动当作注册包。npm torch 与 PyPI torch 不跨生态合并。

数据库仍保留 irrelevant 与 uncertain 的原文、描述、来源、版本和评分。API 根据每个来源记录的最新 assessment 提供筛选，综合展示顺序为 relevant 优先，其次 uncertain，再 irrelevant；并列来源不是人工裁决或概率输出。

V0 不是模型分类器。没有 LLM 调用、人工 gold 标注集或评测运行，所以没有 Precision/Recall/F1/准确率。真实采集主要用于验证链路，普通 CVE 与 malware advisories 也会保留；最终竞争指标须在独立人工真值与冻结评测方案建立后计算。
