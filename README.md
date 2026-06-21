---
name: hermes-production-setup
version: 1.0.0
author: Mimir
---

# Hermes 生产环境配置全景

> 本文件是 Hermes Agent 生产环境的单一权威参考。所有架构决策、模型配置、Cron 任务、监控、知识管理、系统加固、mem0 集成、自建 Skill/Scripts 及踩坑记录均汇总于此。

**核心结论（TL;DR）：**
- 主模型：`LongCat-2.0-Preview` via `custom:Api.longcat.chat`
- Profile：`reasonix`（独立于 default，无 Tavily/mem0）
- 每日 8 个 Cron 任务全部投递飞书，7×24 运行
- 系统加固：IPv4 封禁 7 个恶意 IP + SSH rate-limit + Docker 隔离
- mem0 记忆用 Kimi K2.6（NVIDIA NIM）+ Qdrant 本地向量库
- 自建 9 个 Skill、19 个脚本

---

## 1. 架构决策

### 1.1 多 Provider 架构

采用「主模型 + 辅助任务分离」策略：

| 层级 | 职责 | Provider |
|------|------|----------|
| 主模型 | 用户交互、推理、代码生成 | `custom:Api.longcat.chat` |
| 视觉辅助 | 图片理解 | `nvidia` (Kimi K2.6 via NIM) |
| 知识沉淀 | 记忆压缩/蒸馏 | `deepseek` (deepseek-chat) |
| 轻量子任务 | 标题生成/分类/监控 | `openrouter` (openrouter/free) |
| 网页搜索 | 实时信息检索 | `tavily` (web.backend) |

### 1.2 双 Profile 策略

| Profile | 主模型 | mem0 | Tavily | 用途 |
|---------|--------|------|--------|------|
| `default` | `custom` (LongCat) | ✅ | ✅ | 日常交互 |
| `reasonix` | `custom:Api.longcat.chat` | ❌ | ❌ | 隔离任务/实验 |

### 1.3 关键架构选择

- **Context Engine**: `compressor`（长对话自动压缩）
- **Memory**: `hermes-mem0-local`（本地 Qdrant，不依赖外部 API）
- **Compression**: `threshold=0.5`，启用了 curator（7 天间隔）
- **Delegation**: 最多 50 轮迭代、3 个并发子 agent
- **Security**: Tirith 启用 + secret 自动脱敏

---

## 2. 模型配置要点

### 2.1 主模型

| 字段 | 值 |
|------|------|
| model | `LongCat-2.0-Preview` |
| provider | `custom:Api.longcat.chat` |
| base_url | `https://api.longcat.chat/openai` |
| api_key | `ak_2816hF60...[MASKED]` |
| api_mode | `openai` |

### 2.2 自定义 Providers

| Provider | Model | base_url | api_mode | 备注 |
|----------|-------|----------|----------|------|
| `xf-yun` | `xopqwen36v35b` | `${XF_YUN_BASE_URL}` | openai | 讯飞云，key 从 .env 读 |
| `Api.openmodel.ai` | `deepseek-v4-flash` | `https://api.openmodel.ai/v1` | **anthropic_messages** | ⚠️ 必须 Anthropic 协议 |
| `Api.longcat.chat` | `LongCat-2.0-Preview` | `https://api.longcat.chat/openai` | openai | 主模型 provider |

### 2.3 辅助任务 Provider 路由

| 任务 | Provider | Model |
|------|----------|-------|
| vision | nvidia | `moonshotai/kimi-k2.6` |
| web_extract | auto | (空) |
| compression | deepseek | `deepseek-chat` |
| skills_hub | openrouter | `openrouter/free` |
| approval | deepseek | `deepseek-chat` |
| mcp | deepseek | `deepseek-chat` |
| title_generation | openrouter | `openrouter/free` |
| triage_specifier | openrouter | `openrouter/free` |
| kanban_decomposer | openrouter | `openrouter/free` |
| curator | deepseek | `deepseek-chat` |

### 2.4 TTS

| 字段 | 值 |
|------|------|
| provider | `edge` |
| edge.voice | `en-US-AriaNeural` |

### 2.5 关键限制

- `Api.openmodel.ai` 只支持 Anthropic Messages API（`/v1/messages`），不支持 `/v1/chat/completions`
；Header 用 `x-api-key`，需带 `anthropic-version: 2023-06-01`
- `deepseek-v4-flash` 是 reasoning-only 模型，content 永远为空 → 需要 `deepseek-chat` 或显式 disable thinking
- `openrouter/free` 无 vision 通道 → 需 fallback 到 GLM-4V

---

## 3. Cron 任务清单

> 共 8 个任务，全部 enabled，全部 deliver 到飞书。

| # | 名称 | 时间 (UTC) | 时间 (BJT) | Skill/脚本 | 类型 |
|---|------|-----------|-----------|-----------|------|
| 1 | 📰 每日晨报 | 23:10 | 07:10 | `hermes-daily-morning-report` | 定时+skill |
| 2 | 日志扫描 | 17:20 | 01:20 | `log-daily-scan` | 定时+skill |
| 3 | 🛌 SkillOpt-Sleep weekly | Sun 21:10 | Mon 05:10 | `skillopt-integration` | 每周+skill |
| 4 | ⚽ 世界杯预测(一体化) | 02:30 | 10:30 | `world-cup-predict` | 定时+skill |
| 5 | 🎯 接活雷达+成都招聘(晚间版) | 10:30 | 18:30 | `freelance-radar` | 定时+skill |
| 6 | 📚 IMA知识库更新 | 16:10 | 00:10 | prompt→`hermes-knowledge-update` | 定时+prompt |
| 7 | 📊 模型健康报告 | 18:00 | 02:00 | `model_health.py` | 定时+脚本 |
| 8 | 📊 模型标杆测试 | 22:00 | 06:00 | `model_benchmark.py` | 定时+脚本 |

**投递时间线 (BJT)：**
```
00:10  IMA知识库  01:20  日志扫描  02:00  模型健康
05:10  SkillOpt   06:00  模型标杆  07:10  每日晨报
10:30  世界杯     18:30  接活雷达
```

---

## 4. 监控体系

### 4.1 模型健康报告（每日 02:00 BJT）

- **脚本**: `~/.hermes/scripts/model_health.py --compact`
- **数据源**: `agent.log`（滚动 24h 窗口）
- **输出**: 按模型汇总延迟/错误/用量，紧凑格式投递飞书

### 4.2 模型标杆测试（每日 06:00 BJT）

- **脚本**: `~/.hermes/scripts/model_benchmark.py --compact`
- **测试对象**: LongCat vs MiniMax-M3，7 个固定用例
- **夹具来源**: `extract_benchmark_fixtures.py` 从 `state.db` 提取真实会话
- **历史**: 写入 `~/.hermes/data/benchmark_history.json`

### 4.3 每日系统日报（01:20 BJT）

- **脚本**: `Log_daily_status.py --persist --fix`
- **数据源**: Hermes 日志 + `/var/log/{syslog,auth.log,kern.log}`
- **功能**: LLM/系统状态，修复动作由 agent 独立判断执行

### 4.4 Token 统计

- **脚本**: `token_stats.py --24h --compact`
- **数据源**: `agent.log` + `bounty_tokens.csv`
- **特性**: BJT 凌晨 1:00 自动清零

### 4.5 备份（08:55 BJT，在晨报前完成）

- **脚本**: `backup.sh`
- **备份范围**: `.env | config.yaml | secrets.yaml | memory | skills | cron | scripts | Lab-Analysis`
- **保留策略**: 7 天自动清理

---

## 5. 知识管理

### 5.1 IMA 知识库

- **用途**: 飞书/微信笔记管理、知识沉淀、免费资源灌入
- **Skill**: `ima-skill`（含 `ima_api.cjs` Node.js 客户端）
- **管理脚本**: `ima_kb.py`（CRUD 操作）
- **免费资源灌入**: `ima_seed_free.py`（目标 KB: `RiAyZ6HYD-RRnH1UrNp0gOrHjq5d5nkYoudomp4p6Ek=`）
- **定时任务**: 每天 00:10 BJT 自动更新

### 5.2 LLM 用量分析

- **Skill**: `llm-usage-analysis`
- **功能**: Token 消耗统计、成本分析
- **数据源**: `agent.log`, `bounty_tokens.csv`

### 5.3 Wiki 自动化

- **Skill**: `wiki-automation`
- **功能**: 飞书文档/知识库自动化操作

### 5.4 Curator（自动知识蒸馏）

- **配置**: `enabled: true`, `interval_hours: 168`（7 天）
- **功能**: 自动从对话中提取知识并结构化存储

---

## 6. 系统加固

### 6.1 IPTables 规则

**IPv4 INPUT Chain (policy: ACCEPT):**

| 规则 | 说明 |
|------|------|
| DROP 7 个恶意 IP | `87.251.64.144/145`, `81.90.28.163`, `45.148.10.183`, `47.236.245.255`, `185.204.171.193`, `61.75.245.101`, `59.153.245.232` |
| SSH rate-limit | `recent` 模块：60s 内 4 次新连接 → 封禁 |

**Docker 隔离:**
- FORWARD policy: DROP
- DOCKER chain: DROP all（默认拒绝）
- 只允许 RELATED,ESTABLISHED 的容器流量

**IPv6 状态:** ⚠️ 所有链为空，policy ACCEPT — IPv6 流量不受限制（待加固）。

### 6.2 密钥保护

- **完整性校验**: `check_secret_integrity.sh`（sha256 校验，不打印明文）
- **脱敏**: Hermes `redact_secrets: true` 自动脱敏
- **存储**: 敏感信息通过 `.env` 环境变量注入，不写入配置文件

---

## 7. mem0 集成

### 7.1 架构

```
用户消息 → Hermes Agent
                ↓
         mem0 wrapper.py
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
  LLM        Embedder    Vector Store
(Kimi K2.6) (MiniLM-L6)  (Qdrant)
    ↓           ↓           ↓
  记忆生成     384维嵌入   持久化存储
                ↓
         History Store (SQLite)
```

### 7.2 配置

| 组件 | 值 |
|------|------|
| LLM Provider | `openai` |
| LLM Model | `moonshotai/kimi-k2.6` |
| LLM base_url | `https://integrate.api.nvidia.com/v1` |
| LLM api_key | `${NVIDIA_API_KEY}`（从 .env 注入） |
| LLM temperature | `0.1` |
| LLM max_tokens | `2000` |
| Embedder | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | `qdrant`（on_disk: true） |
| Qdrant Path | `/root/.mem0/qdrant` |
| Collection | `hermes_memories` |
| Embedding Dims | `384` |
| History DB | `/root/.mem0/history.db` |
| Default User | `nie_dan` |

### 7.3 Hermes 记忆配置

| 字段 | 值 |
|------|------|
| memory.provider | `hermes-mem0-local` |
| memory_enabled | `true` |
| user_profile_enabled | `true` |
| memory_char_limit | `2200` |
| user_char_limit | `1375` |

---

## 8. 自建 Skill 清单

> 共 9 个自建/深度修改 Skill，位于 `~/.hermes/skills/`。

| Skill | 大小 | 说明 |
|-------|------|------|
| **auxiliary-model-diagnosis** | 35.7KB | 12 个 auxiliary sub-task 诊断（provider 路由/凭证验证/踩坑） |
| **ima-skill** | 24.9KB | IMA 知识库集成（飞书/微信笔记 CRUD + 知识灌入） |
| **skillopt-integration** | 26.9KB | SkillOpt-Sleep 集成（17 条踩坑 + cron 集成） |
| **llm-usage-analysis** | 12.7KB | LLM Token 消耗与成本分析 |
| **public-figure-investigation** | 11.1KB | 公众人物信息调查与结构化输出 |
| **gateway-restart-vs-reload** | 8.8KB | Gateway 重启 vs 重载（SIGUSR1 vs systemd 全重启） |
| **github-pr-contributions** | 8.3KB | GitHub PR 管理与贡献统计 |
| **wiki-automation** | 3.5KB | 飞书文档/知识库自动化 |
| **agent-reach** | 5.0KB | 多渠道消息触达 |

**注意**: `reasonix` profile 的 `memory.provider` 为空，上述依赖 mem0 的 skill 在 reasonix profile 下可能无法正常工作。

---

## 9. 自建脚本清单

> 共 19 个脚本，位于 `~/.hermes/scripts/`。

### 9.1 核心脚本

| # | 脚本 | 用途 | 关键参数 |
|---|------|------|----------|
| 1 | `model_benchmark.py` | 模型标杆测试 v2（LongCat vs MiniMax-M3） | `--models` `--compact` `--extract` |
| 2 | `extract_benchmark_fixtures.py` | 从 state.db 提取真实会话做 benchmark 夹具 | — |
| 3 | `model_health.py` | 模型健康报告 v2（延迟/错误/用量） | `--hours 72` `--days 7` `--compact` |
| 4 | `Log_daily_status.py` | 每日 LLM/系统日报 | `--persist` `--fix` |
| 5 | `token_stats.py` | Token 统计 v5（按 LLM×Provider） | `--24h` `--compact` |
| 6 | `predict_wc.py` | World Cup 预测引擎 v2 | `--dates` `--no-fetch` |
| 7 | `ima_kb.py` | IMA 知识库 CRUD | `{list_notebooks,search_notes,...}` |
| 8 | `ima_seed_free.py` | 灌入免费 AI Token 资源到 IMA | — |
| 9 | `genimg.py` | 免费图生包装（Pollinations/Dashscope） | — |
| 10 | `dl_tongyi.py` | 下载通义万相图片 | — |
| 11 | `longcat_thinking_test.py` | LongCat thinking 污染复现测试 | — |
| 12 | `longcat_thinking_test.sh` | LongCat thinking 测试（Shell 版） | — |

### 9.2 运维脚本

| # | 脚本 | 用途 |
|---|------|------|
| 13 | `backup.sh` | 每日备份（7 天保留） |
| 14 | `openhands-run` | 一键派活给 OpenHands（OpenRouter） |
| 15 | `log_daily_status_cron.sh` | Log_daily_status.py 的 cron 包装 |
| 16 | `check_secret_integrity.sh` | 密钥完整性校验 |
| 17 | `bw_unlock.sh` | Bitwarden 解锁 |
| 18 | `jina-fetch.sh` | Jina Reader API 包装 |
| 19 | `hindsight-upgrade.sh` | Hindsight Docker 升级 |

---

## 10. 踩坑记录汇总

> 每条踩坑含现象 / 根因 / 修复 / 验证。按类别分组。

### 10.1 API Key 相关

#### C1: DeepSeek key 末尾的 `\n`
- **现象**: OpenAI SDK 返回 `401 Incorrect API key`
- **根因**: `.env` 写入时尾部带换行符，SDK 直传整串（35 字符 key + 1 字节 `\n`）
- **修复**: Python 提取用 `line.split(chr(61), 1)[1].rstrip()`，**不**走 shell `export KEY=$(grep ...)`
- **验证**: DeepSeek 把中间掩盖为 23 个 `*`（非默认 8-12），确认 SDK 看到带尾部 `*` 的字符串

#### C2: API Key 不能在 terminal 传 `***` 值
- **现象**: `ANTHROPIC_API_KEY=***sk-abc...` 执行后 API 返回 401
- **根因**: Hermes 渲染层在 `***` 处截断字符串，shell 拿到不完整的 key
- **修复**: 用 Python 从 `config.yaml` 读取后通过 `subprocess.run(cmd, env=env)` 注入
- **验证**: 用 `python3 -c "..."` 预提取 key 再传 env，401 消失

### 10.2 模型相关

#### C3: `deepseek-v4-flash` 是 reasoning-only
- **现象**: API 返回 200 + 空 content
- **根因**: reasoning-only 模型把所有 token 用在 `reasoning_tokens`，`completion_tokens` = 0
- **修复**: 换 `deepseek-chat` 或显式 `extra_body={"thinking": {"type": "disabled"}}`
- **验证**: 响应 `usage` 字段 `reasoning_tokens=100, completion_tokens=100, content=空`

#### C4: LongCat thinking 污染
- **现象**: LongCat-2.0-Preview content 干净，但存在 `thinking: false` bug
- **根因**: 非 thinking 模型却带 thinking 字段
- **修复**: 脚本 `longcat_thinking_test.py` 复现确认
- **验证**: 输出在 `/root/.hermes/data/longcat_thinking_test/`

#### C5: `openrouter/free` vision 404
- **现象**: `auxiliary.vision` 用 `openrouter/free` 返回 404 "no channel available"
- **根因**: `openrouter/free` 路由到免费模型池，无 vision-capable 通道
- **修复**: 切换到 GLM-4V（`openrouter/glm-4v`, base_url: `https://open.bigmodel.cn/api/paas/v4/`）
- **验证**: GLM-4V 限制最大 ~8MB 输入，大图需 resize 到 800px

#### C6: `Api.openmodel.ai` 协议不对称
- **现象**: `/v1/chat/completions` 返回 404，`/v1/messages` 正常
- **根因**: openmodel.ai 只支持 Anthropic Messages API
- **修复**: `api_mode: anthropic_messages`，header `x-api-key`，带 `anthropic-version: 2023-06-01`
- **验证**: 可换为真 Claude 模型（`claude-opus-4-8` 等）

#### C7: `Api.qnaigc.com` model channel mismatch
- **现象**: HTTP 400 "no available channels for model GLM-4.7-Flash"
- **根因**: qnaigc 的通道是模型粒度的，`GLM-4.7-Flash` 无通道
- **修复**: 使用 provider 默认 model 或确认目标 model 有可用通道
- **验证**: `z-ai/glm-5` 有通道

### 10.3 Cron 相关

#### C8: `script: null` 误填
- **现象**: cron 报 "Script not found: python3 /root/.../Log_daily_status.py --persist --fix"
- **根因**: jobs.json 里 `script` 字段被填了完整命令，Hermes 把整串当裸路径查
- **修复**: `script: null`（走 prompt），或 `script: <abs path>` + `args: [...]` + `no_agent: true`
- **验证**: 写 jobs.json 后立刻 `cronjob run <id>` 手动跑一次

#### C9: `deliver=local` 的 cron 看不到结果
- **现象**: 跑成功但用户完全收不到通知
- **根因**: `deliver=local`= 仅写本地 output 目录，不推送任何 channel
- **修复**: 建 cron 前先想好"我怎么知道跑成功了"，deliver 设为飞书/channel
- **验证**: 当前全部 8 个 cron 均 deliver 飞书

#### C10: 老 inline prompt（>100 行）会截断
- **现象**: cron LLM agent 跑到一半 token 超限，输出 `[truncated]`
- **根因**: prompt inline 写所有约束，长度超 4K token
- **修复**: 把大段指令移到 markdown 文件，prompt 改成 `读取 /path/to/instructions.md`
- **验证**: 分离后 cron 输出完整无截断

#### C11: cron 时间要匹配事件时序
- **错误思维**: "用户 BJT 09:30 买彩票 → 预测应该在 09:00 跑"
- **正确思维**: "预测要拿'开赛前 2h 临场盘' → 应该比赛**前 2h**跑"
- **修复**: 根据事件时间倒推 cron 时间

#### C12: judge 的 reference 格式必须明确
- **现象**: candidate "Switzerland wins" vs reference "Switzerland 胜" → 判 0 分
- **修复**: reference 用英文跟 output 对齐，或用 `reference_kind="rule"` 写 rubric
- **验证**: 对齐后评分正确

### 10.4 Gateway 相关

#### C13: `hermes gateway restart` ≠ 全重启
- **现象**: 改了平台配置后 restart，平台连接仍断开
- **根因**: restart 发送 SIGUSR1 → 只重载 `.env` 和 `config.yaml`，不重建平台适配器
- **修复**: 平台连接断开时用 `systemctl --user stop hermes-gateway && systemctl --user start hermes-gateway`
- **验证**: `restart` 会 spawn 新 PID，但飞书 WebSocket / 微信 poll loop 不重建

#### C14: `systemctl --user reload` = SIGUSR1
- 等价于 `hermes gateway restart`，都不重建平台适配器

### 10.5 SkillOpt-Sleep 相关

#### C15: `get_backend` 是 hardcoded
- **现象**: 注册新 backend 名后报 "Unknown backend"
- **根因**: `cycle.py` 只有 `claude-cli` / `codex-cli` / `copilot-cli` 三选一
- **修复**: monkey-patch `get_backend` 函数

#### C16: `TaskRecord` 字段名不符
- **现象**: `TypeError: __init__() got unexpected keyword argument 'source'`
- **修复**: 用 `project`（不是 `source`）；`outcome` 可选

#### C17: `SleepConfig.data` 必填字段
- 必须包含: `claude_home`, `state_dir`, `backend`, `model`, `nights`, `max_tasks_per_night`, `rollouts_k`, `holdout_fraction`, `gate_mode`, `edit_budget`, `managed_skill_name`

#### C18: 循环论证
- **现象**: candidate score == baseline score 恒成立，gate 永远 reject
- **根因**: 把 LLM 自己的预测当 reference
- **修复**: 必须 join 真实 ground truth（外部 API 抓的实际结果）

#### C19: SKILL.md version 字段必须为整数
- **现象**: `ValidationError: Input should be a valid integer, unable to parse string as an integer [input_value='2.0.0']`
- **根因**: Pydantic `SkillMetadata.version` 定义成 `int` 类型
- **修复**: `content.replace('version: 2.0.0', 'version: 2')`

#### C20: 接新 OpenAI 兼容 provider 的 4 步法
1. 复制 `templates/openai_compat_backend.py`
2. export `SKILLOPT_OPENAI_API_KEY` / `BASE_URL` / `MODEL`
3. 入口脚本 `from skillopt_sleep.openai_compat_backend import patch_get_backend; patch_get_backend(target_name="<name>")`
4. `SleepConfig(data={..., "backend": "<name>", ...})`

#### C21: 同一 session 多次跑 cycle → state 累积
- **修复**: 每次跑前 `rm -rf state_dir`

#### C22: Reference/consultation skills 不适合 skill-evolution
- **原因**: evaluator 测试模型自身训练知识，不是 skill 文本内容
- **适合 evolution**: 流程型（有明确步骤顺序）
- **不适合**: 参考型（纯信息罗列）、混合大型（>30KB）

### 10.6 Hindsight 相关

#### C23: Hindsight Docker 升级踩坑
- 仓库只发布 `:latest`/`:latest-slim`，无版本号 tag → 不能 pin 版本
- 默认 worker ID = 容器 hostname → Docker 重启会变 → zombie operations
- `retain_async=true` 会让 LLM 失败时 silent drop

---

## 11. 新环境快速上手

### 11.1 首次部署 Checklist

1. **安装 Hermes Agent** — 参照官方文档完成基础安装
2. **配置 Provider** — 在 `~/.hermes/config.yaml` 中设置主模型（`custom:Api.longcat.chat`）和辅助 providers
3. **设置环境变量** — `.env` 文件包含所有 API keys（`NVIDIA_API_KEY`, `XUNFEI_API_KEY` 等）
4. **导入 Profile** — 选择 `default`（有 mem0 + Tavily）或 `reasonix`（隔离模式）
5. **初始化 mem0** — Qdrant 数据目录 `/root/.mem0/qdrant` 会自动创建
6. **配置 IPTables** — 封禁恶意 IP + SSH rate-limit + Docker 隔离
7. **注册 Cron 任务** — 8 个任务按时间表 3 部署
8. **安装自建 Skill** — 将 `~/.hermes/skills/` 下 9 个 skill 复制到位
9. **安装自建脚本** — 将 `~/.hermes/scripts/` 下 19 个脚本复制到位
10. **配置备份** — `backup.sh` 设置每日自动备份
11. **测试** — 手动触发每个 cron 任务验证端到端

### 11.2 防御性编码速查

| # | 规则 |
|---|------|
| 1 | 写 skill 前先 `python3 -c "import skillopt_sleep; print(skillopt_sleep.__file__)"` 确认路径 |
| 2 | 跑 cycle 前先 `python -m skillopt_sleep.experiments.run_experiment --persona researcher --assert-improves` |
| 3 | 写 cron 后立刻 `cronjob run <id>` 手动跑一次 |
| 4 | 改 jobs.json 后 `cp jobs.json jobs.json.bak.<ts>` 备份 |
| 5 | skill 文档的 support files 必须真存在 — 占位文件会让 agent 扑空 |
| 6 | **永远不要**在 terminal 命令里 inline 写 API key |
| 7 | DeepSeek key 用 `rstrip()` 去除尾部 `\n` |

### 11.3 常见问题排查

| 症状 | 排查方向 |
|------|----------|
| API 401 | key 尾部 `\n`？`***` 截断？ |
| 空 content | reasoning-only 模型？需 disable thinking |
| Cron 无输出 | `deliver=local`？prompt 超 4K token？ |
| 平台连接断开 | 需 `systemctl --user stop && start`，不是 `restart` |
| Skill 文件不存在 | 检查 SKILL.md 中 support files 是否都是真实文件 |
| IPv6 未防护 | ip6tables 仍为空，需要额外配置 |

### 11.4 关键路径速查

| 资源 | 路径 |
|------|------|
| 配置文件 | `~/.hermes/config.yaml` |
| Profile | `~/.hermes/profiles/{default,reasonix}/config.yaml` |
| 环境变量 | `~/.hermes/.env` |
| 日志 | `~/.hermes/logs/{agent,gateway,errors}.log` |
| Skills | `~/.hermes/skills/` |
| Scripts | `~/.hermes/scripts/` |
| Cron | `~/.hermes/cron/` |
| mem0 向量库 | `/root/.mem0/qdrant/` |
| mem0 历史 | `/root/.mem0/history.db` |
| 备份 | `~/.hermes/backups/` |
| 数据 | `~/.hermes/data/` |
| Benchmark 历史 | `~/.hermes/data/benchmark_history.json` |
