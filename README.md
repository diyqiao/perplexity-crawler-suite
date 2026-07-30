# Perplexity API 集成指南 (Antigravity) - 省钱极客版 💡

本项目已为你配置好最零依赖、高效且**极致省钱**的 Perplexity API 集成脚本 `pplx.py` 与 MCP (Model Context Protocol) 协议配置。

---

## 💰 最省钱调用策略 (Cost Optimization)

脚本内置了 4 大自动省钱机制：
1. **默认使用最廉价模型**：默认采用 `sonar` 模型（相比 `sonar-pro` / `sonar-reasoning` 价格大幅降低，仅为零头）。
2. **本地磁盘缓存 (⚡ Local Cache)**：相同问题重复查询直接读取本地缓存 `.pplx_cache.json`，**0 API 调用费，0 延迟**。
3. **输出 Token 数量控制 (`--max-tokens`)**：默认限制最大输出为 500 Token，防止 API 生成大量长篇废话扣费。
4. **精简提示词 (System Prompt Optimization)**：Prompt 约束模型直接输出干货，极大缩减 Response Tokens。

---

## ⚡ 1. 配置你的 API Key

在终端 (PowerShell) 中运行以下命令设置环境变量：

```powershell
$env:PERPLEXITY_API_KEY="pplx-你的Perplexity_API密钥"
```

---

## 🚀 2. 使用方式

### 方式 A：命令行调用 (CLI)

```bash
# 1. 默认最省钱搜索 (使用 sonar + 本地缓存 + 500 token 限制)
python pplx.py "2026年最新AI技术趋势"

# 2. 限制回答更短 (进一步省钱，如限制 200 token)
python pplx.py "量子计算最新突破" --max-tokens 200

# 3. 绕过缓存强制刷最新联网数据
python pplx.py "今日最新科技新闻" --no-cache

# 4. 需要高级推理时显式指定模型
python pplx.py "复杂数学证明或深入架构对比" --model sonar-pro

# 5. 清理本地缓存
python pplx.py --clear-cache
```

---

### 方式 B：在对话中吩咐 Antigravity Agent

在对话中直接要求 Agent 时，Agent 会自动通过 MCP 或脚本触发省钱模式：
> *"帮我用 Perplexity API 查询一下最省钱的模式下，最新的 AI 框架对比"*

