# Mem0 配置参考

> 数据来源：`~/.hermes/mem0/config.yaml`
> 提取时间：2026-06-21
> 加载方式：`~/.hermes/mem0/wrapper.py` 从这个文件读取
> 完整文档：`~/.hermes/skills/memory/mem0-integration/SKILL.md`

---

## LLM 配置

| 字段 | 值 |
|------|------|
| **provider** | `openai` |
| **model** | `moonshotai/kimi-k2.6` |
| **api_key** | `${NVIDIA_API_KEY}` (从 `/root/.hermes/.env` 读取) |
| **openai_base_url** | `https://integrate.api.nvidia.com/v1` |
| **temperature** | `0.1` |
| **max_tokens** | `2000` |

> ⚠️ 换 LLM 只需改上面 4 个字段：provider / model / api_key / openai_base_url。其他字段不要动。

---

## Embedder 配置

| 字段 | 值 |
|------|------|
| **provider** | `huggingface` |
| **model** | `sentence-transformers/all-MiniLM-L6-v2` |

---

## Vector Store 配置

| 字段 | 值 |
|------|------|
| **provider** | `qdrant` |
| **path** | `/root/.mem0/qdrant` |
| **embedding_model_dims** | `384` |
| **collection_name** | `hermes_memories` |
| **on_disk** | `true` |

---

## History Store 配置

| 字段 | 值 |
|------|------|
| **path** | `/root/.mem0/history.db` |

---

## 默认用户

| 字段 | 值 |
|------|------|
| **user_id** | `nie_dan` |

---

## 架构总结

```
用户消息 → Hermes Agent
                ↓
         mem0 wrapper.py
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
  LLM        Embedder    Vector Store
(Kimi K2.6) (MiniLM-L6)  (Qdroid)
    ↓           ↓           ↓
  记忆生成     384维嵌入   持久化存储
    ↓           ↓           ↓
    └───────────┼───────────┘
                ↓
         History Store
         (SQLite: history.db)
```

---

## 注意事项

1. **API Key**：通过环境变量 `NVIDIA_API_KEY` 注入，不写在配置文件里
2. **模型**：当前用 NVIDIA NIM 代理的 `moonshotai/kimi-k2.6`（Kimi K2.6）
3. **嵌入维度**：384 维（all-MiniLM-L6-v2 的固定输出维度）
4. **存储**：Qdrant 使用磁盘模式（`on_disk: true`），数据持久化在 `/root/.mem0/qdrant`
5. **多用户**：当前默认 user_id 为 `nie_dan`，多用户场景可改 `defaults.user_id`
