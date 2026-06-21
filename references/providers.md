# Provider 配置参考

> 数据来源：`~/.hermes/config.yaml` (model 段 + custom_providers 段)
> 提取时间：2026-06-21
> ⚠️ API Key 仅保留前8位 + `...[MASKED]`

---

## 1. 主模型配置 (Top-level `model`)

| 字段 | 值 |
|------|------|
| **default** | `LongCat-2.0-Preview` |
| **provider** | `custom` |
| **base_url** | `https://api.longcat.chat/openai` |
| **api_key** | `ak_2816hF60...[MASKED]` |
| **api_mode** | `openai` |

---

## 2. 自定义 Providers (`custom_providers`)

### 2.1 xf-yun（讯飞云）

| 字段 | 值 |
|------|------|
| **name** | `xf-yun` |
| **base_url** | `${XF_YUN_BASE_URL}` (从 .env 读取) |
| **api_key** | `${XUNFEI_API_KEY}` (从 .env 读取) |
| **model** | `xopqwen36v35b` |

### 2.2 Api.openmodel.ai

| 字段 | 值 |
|------|------|
| **name** | `Api.openmodel.ai` |
| **base_url** | `https://api.openmodel.ai/v1` |
| **api_key** | `om-2wW4FgEF...[MASKED]` |
| **model** | `deepseek-v4-flash` |
| **api_mode** | `anthropic_messages` ⚠️ 必须用 Anthropic 协议，OpenAI 协议会 404 |

> **踩坑**：openmodel.ai 只支持 Anthropic Messages API (`/v1/messages`)，不支持 `/v1/chat/completions`。Header 用 `x-api-key`（不是 `Authorization: Bearer`），且需带 `anthropic-version: 2023-06-01`。

### 2.3 Api.longcat.chat

| 字段 | 值 |
|------|------|
| **name** | `Api.longcat.chat` |
| **base_url** | `https://api.longcat.chat/openai` |
| **api_key** | `ak_2816hF60...[MASKED]` |
| **model** | `LongCat-2.0-Preview` |
| **api_mode** | `openai` |

---

## 3. Auxiliary Sub-task Providers

这些是 Hermes 内部辅助任务使用的 provider，配置在 `auxiliary` 段：

| 任务 | provider | model | 备注 |
|------|----------|-------|------|
| **vision** | `nvidia` | `moonshotai/kimi-k2.6` | 通过 NVIDIA NIM |
| **web_extract** | `auto` | (空) | 运行时自动选择 |
| **compression** | `deepseek` | `deepseek-chat` | 非 reasoning 模型 |
| **skills_hub** | `openrouter` | `openrouter/free` | 免费模型 |
| **approval** | `deepseek` | `deepseek-chat` | 严格格式输出 |
| **mcp** | `deepseek` | `deepseek-chat` | — |
| **title_generation** | `openrouter` | `openrouter/free` | — |
| **tts_audio_tags** | `openrouter` | `openrouter/free` | — |
| **triage_specifier** | `openrouter` | `openrouter/free` | — |
| **kanban_decomposer** | `openrouter` | `openrouter/free` | — |
| **profile_describer** | `openrouter` | `openrouter/free` | — |
| **curator** | `deepseek` | `deepseek-chat` | — |
| **monitor** | `auto` | (空) | — |

---

## 4. TTS Provider

| 字段 | 值 |
|------|------|
| **provider** | `edge` |
| **edge.voice** | `en-US-AriaNeural` |

---

## 5. MCP Servers

| Server | 连接方式 | 说明 |
|--------|----------|------|
| **agentmail** | `npx -y agentmail-mcp` | 邮件收发 |
| **scrapling** | `http://127.0.0.1:8000/mcp` | 网页抓取（HTTP/Stealth/Playwright） |
| **jina** | `https://mcp.jina.ai/v1` | Jina AI 搜索/阅读/图片/截图 |
| **time** | `uvx mcp-server-time` | 时区转换 |

---

## 6. 其他关键配置

| 配置项 | 值 |
|--------|------|
| **context.engine** | `compressor` |
| **memory.provider** | `hermes-mem0-local` |
| **memory.memory_enabled** | `true` |
| **memory.user_profile_enabled** | `true** |
| **memory.memory_char_limit** | `2200` |
| **memory.user_char_limit** | `1375` |
| **agent.max_turns** | `90` |
| **agent.gateway_timeout** | `1800` |
| **agent.reasoning_effort** | `medium` |
| **compression.enabled** | `true` |
| **curator.enabled** | `true** |
| **curator.interval_hours** | `168` (7天) |
| **stt.enabled** | `true` |
| **stt.provider** | `local` |
| **web.backend** | `tavily` |
| **x_search.model** | `grok-4.20-reasoning` |
| **image_gen.provider** | `openai-codex` |
| **image_gen.model** | `gpt-image-2-medium` |
