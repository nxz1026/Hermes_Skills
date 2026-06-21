# Reasonix Profile 配置参考

> 数据来源：`~/.hermes/profiles/reasonix/config.yaml`
> 提取时间：2026-06-21

---

## 1. 模型配置

| 字段 | 值 |
|------|------|
| **model.default** | `LongCat-2.0-Preview` |
| **model.provider** | `custom:Api.longcat.chat` |

> 注意：provider 格式为 `custom:Api.longcat.chat`，表示使用 `custom_providers` 中名为 `Api.longcat.chat` 的 provider。

---

## 2. 与 default profile 差异

| 配置项 | default | reasonix |
|--------|---------|----------|
| **model.provider** | `custom` | `custom:Api.longcat.chat` |
| **web.backend** | `tavily` | (空) |
| **memory.provider** | `hermes-mem0-local` | (空) |
| **logging.level** | `INFO` | `INFO` |
| **logging.max_size_mb** | `5` | `5` |
| **logging.backup_count** | `3` | `3` |
| **model_catalog.enabled** | `true` | `true` |
| **model_catalog.url** | `https://hermes-agent.nousresearch.com/docs/api/model-catalog.json` | 同 |
| **gateway.message_timestamps.enabled** | `false` | `false` |
| **gateway.strict** | `false` | `false` |
| **network.force_ipv4** | `false` | `false` |

---

## 3. 关键差异说明

1. **provider 不同**：reasonix 显式指定 `custom:Api.longcat.chat`，而 default 用 `custom`（走主模型配置）
2. **web.backend**：reasonix 未配置 Tavily 搜索后端
3. **memory.provider**：reasonix 未配置 mem0，记忆功能可能不生效
4. **其余配置**：与 default profile 基本一致（toolsets、agent、terminal、auxiliary 等完全相同）

---

## 4. 共享配置（两 profile 相同）

- **auxiliary**：12 个辅助任务的 provider/model 配置完全相同
- **display**：界面设置相同
- **tts/stt**：语音配置相同
- **approvals**：`mode: smart`, `timeout: 60`
- **compression**：`enabled: true`, `threshold: 0.5`
- **delegation**：`max_iterations: 50`, `max_concurrent_children: 3`
- **security**：`tirith_enabled: true`, `redact_secrets: true`
- **cron**：`wrap_response: true`
