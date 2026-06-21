# 关键踩坑记录

> 数据来源：
> - `~/.hermes/skills/skillopt-integration/references/pitfalls.md` (17 条 SkillOpt 踩坑)
> - `~/.hermes/skills/auxiliary-model-diagnosis/SKILL.md` (辅助模型诊断踩坑)
> - `~/.hermes/skills/gateway-restart-vs-reload/SKILL.md` (Gateway 重启踩坑)
> - `~/.hermes/scripts/hindsight-upgrade.sh` (Hindsight 升级踩坑)
> - `~/.hermes/scripts/longcat_thinking_test.py` (LongCat thinking 测试)
> - `~/.hermes/config.yaml` 注释中的 Fallback Model 说明
> 提取时间：2026-06-21

---

## 一、API Key 相关

### 1. DeepSeek key 末尾的 `\n`（最常见）
- **现象**：OpenAI SDK 拿 key 调 API 返回 `401 Incorrect API key`
- **根因**：`.env` 写入时尾部带换行符，OpenAI SDK 直传整串（35 字符 key + 1 字节 `\n` = 36 字节）
- **错误信息确认**：DeepSeek 把中间掩盖为 23 个 `*`（不是默认 8-12），说明 SDK 看到的是带尾部 `*` 的字符串
- **修法**：脚本里用 Python 提取（`line.split(chr(61), 1)[1].rstrip()`），**不要走 shell `export KEY=$(grep ...)`**（shell 不自动剥行尾 `\n`）

### 2. API Key 不能在 terminal 传 `***` 值
- **现象**：`ANTHROPIC_API_KEY=***sk-abc...` 执行后 API 返回 401
- **根因**：Hermes 渲染层在 `***` 处截断字符串，shell 实际拿到不完整的 key
- **修法**：**永远不要**在 terminal 命令里 inline 写 key。用 Python 从 `config.yaml` 读取后通过 `subprocess.run(cmd, env=env)` 注入。或者先 `export KEY=$(python3 -c "import yaml; print(...)"` 再跑 CLI

---

## 二、模型相关

### 3. `deepseek-v4-flash` 是 reasoning-only（隐藏炸弹）
- **现象**：API 返回 200 + 空 content
- **根因**：reasoning-only 模型把所有 token 用在 `reasoning_tokens`（内部思考），`completion_tokens` 永远 = 0
- **验证**：响应 `usage` 字段里 `reasoning_tokens=100, completion_tokens=100, content=空字符串`
- **修法**：换 `deepseek-chat`（普通模型）或**显式 `extra_body={"thinking": {"type": "disabled"}}`**
- **影响范围**：所有 `max_tokens < 50` 的调用都可能触发此问题

### 4. LongCat thinking 污染
- **测试日期**：2026-06-20
- **结论**：LongCat-2.0-Preview content 干净，但存在 `thinking: false` bug
- **测试脚本**：`~/.hermes/scripts/longcat_thinking_test.py` + `.sh`
- **输出**：`/root/.hermes/data/longcat_thinking_test/`

### 5. `openrouter/free` vision 404
- **现象**：`auxiliary.vision` 用 `openrouter/free` 返回 404 "no channel available"
- **根因**：`openrouter/free` 路由到免费模型池，不一定有 vision-capable 通道
- **修法**：切换到 GLM-4V（`provider: openrouter`, `model: glm-4v`, `base_url: https://open.bigmodel.cn/api/paas/v4/`）
- **GLM-4V 限制**：最大 ~8MB 输入，大图需先 resize 到 800px

### 6. `Api.openmodel.ai` 协议不对称
- **现象**：`/v1/chat/completions` 返回 404，但 `/v1/messages` 正常
- **根因**：openmodel.ai 只支持 Anthropic Messages API 协议
- **正确配置**：`api_mode: anthropic_messages`，header 用 `x-api-key`（不是 `Authorization: Bearer`），需带 `anthropic-version: 2023-06-01`
- **发现**：openmodel.ai 上可换为真 Claude 模型（`claude-opus-4-8` 等）

### 7. `Api.qnaigc.com` model channel mismatch
- **现象**：HTTP 400 "no available channels for model GLM-4.7-Flash"
- **根因**：qnaigc 的通道是模型粒度的，`GLM-4.7-Flash` 无通道但 `z-ai/glm-5` 有
- **修法**：使用 provider 默认 model 或确认目标 model 有可用通道

---

## 三、Cron 相关

### 8. `script: null` 误填
- **现象**：cron 报 "Script not found: python3 /root/.../Log_daily_status.py --persist --fix"
- **根因**：jobs.json 里 `script` 字段被填了"命令"（带 `python3` 前缀 + 参数），Hermes 把整串当裸路径查
- **修法**：要么 `script: null`（走 `prompt` 走 shell），要么 `script: <abs path>` + `args: [...]` + `no_agent: true`
- **校验建议**：写 jobs.json 后立刻 `cronjob run <id>` 试一次，**不**等 next_run

### 9. `deliver=local` 的 cron 看不到结果
- **现象**：cron 跑成功但用户完全收不到任何通知
- **根因**：`deliver=local` = 仅写本地 output 目录，不推送任何 channel
- **教训**：建 cron 前先想清楚"我**怎么**知道它跑成功了"

### 10. 老 inline prompt（>100 行）会截断
- **现象**：cron LLM agent 跑到一半 token 超限，输出被截断成 `[truncated]`
- **根因**：prompt inline 写所有约束，长度超 4K token
- **修法**：把大段指令移到 markdown 文件，prompt 改成 `读取 /path/to/instructions.md 获取完整指令`

### 11. cron 时间要匹配事件时序
- **错误思维**："用户 BJT 09:30 买彩票 → 预测应该在 09:00 跑"
- **正确思维**："预测要拿'开赛前 2h 临场盘' → 应该比赛**前 2h**跑"

### 12. judge 的 reference 格式必须明确
- **现象**：candidate 输出 "Switzerland wins" vs reference "Switzerland 胜" → 判 0 分
- **修法**：reference 用英文跟 output 对齐，要么用 `reference_kind="rule"` 写 rubric

---

## 四、Gateway 相关

### 13. `hermes gateway restart` ≠ 全重启
- **现象**：改了平台配置后 `hermes gateway restart`，平台连接仍然断开
- **根因**：`restart` 发送 SIGUSR1 → 只重载 `.env` 和 `config.yaml`，**不重建平台适配器**（飞书 WebSocket、微信 poll loop 等）
- **修法**：平台连接断开时用 `systemctl --user stop hermes-gateway && systemctl --user start hermes-gateway`
- **注意**：`hermes gateway restart` 确实会 spawn 新 PID（不是进程内重载），但平台连接不重建

### 14. `systemctl --user reload` = SIGUSR1
- `systemctl --user reload hermes-gateway` 等价于 `hermes gateway restart`，都不重建平台适配器

---

## 五、SkillOpt-Sleep 相关

### 15. `get_backend` 是 hardcoded
- **现象**：注册新 backend 名后 `run_sleep_cycle()` 报 "Unknown backend"
- **根因**：`cycle.py` 里只有 `claude-cli` / `codex-cli` / `copilot-cli` 三选一
- **修法**：monkey-patch `get_backend` 函数

### 16. `TaskRecord` 字段名
- **现象**：`TypeError: __init__() got unexpected keyword argument 'source'`
- **真实字段**：`id, project, intent, context_excerpt, reference, reference_kind, outcome, ...`
- 没有 `source`（用 `project`）；`outcome` 可选

### 17. `SleepConfig.data` 必填字段
- **必填**：`claude_home`, `state_dir`, `backend`, `model`, `nights`, `max_tasks_per_night`, `rollouts_k`, `holdout_fraction`, `gate_mode`, `edit_budget`, `managed_skill_name`

### 18. 循环论证（ground truth 来自 LLM 自己的预测）
- **现象**：candidate score == baseline score 恒成立，gate 永远 reject
- **根因**：把 LLM 自己的预测当 reference，agent 复述自己当然"对"
- **修法**：必须 join 真实 ground truth（外部 API 抓的实际结果）

### 19. SKILL.md version 字段必须为整数
- **现象**：`skill-evolution evolve` 报 `ValidationError: Input should be a valid integer, unable to parse string as an integer [input_value='2.0.0']`
- **根因**：`SkillMetadata` 的 Pydantic model 把 `version` 定义成 `int` 类型
- **修法**：`content.replace('version: 2.0.0', 'version: 2')`

### 20. 接新 OpenAI 兼容 provider 的 4 步法
1. 复制 `templates/openai_compat_backend.py` 到 `skillopt_sleep/openai_compat_backend.py`
2. 启动前 export 3 个环境变量：`SKILLOPT_OPENAI_API_KEY` / `SKILLOPT_OPENAI_BASE_URL` / `SKILLOPT_OPENAI_MODEL`
3. 入口脚本加 `from skillopt_sleep.openai_compat_backend import patch_get_backend; patch_get_backend(target_name="<your-name>")`
4. `SleepConfig(data={..., "backend": "<your-name>", ...})`

### 21. 同一 session 多次跑 cycle → state 累积
- 第二次跑会从旧 cycle 接着改
- **修法**：每次跑前 `rm -rf state_dir`

### 22. Reference/consultation skills 不适合 skill-evolution
- **原因**：evaluator 测试的是模型能不能回答（模型自身训练知识），不是 skill 文本中有没有这段
- **结果**：保护任务越多 → 进化越觉得"无所谓" → 砍越狠（51KB→10KB，-80%）
- **适合 evolution 的 skill 类型**：流程型（有明确步骤顺序）
- **不适合的**：参考型（纯信息罗列）、混合大型（>30KB）

---

## 六、Hindsight 相关

### 23. Hindsight Docker 升级踩坑
- 仓库只发布 `:latest` 和 `:latest-slim`，无版本号 tag → 不能 pin 版本
- `docker pull` 不会主动检测"有新版本" — 必须看 GH releases
- 默认 worker ID = 容器 hostname → Docker 重启会变 → zombie operations
- `retain_async=true` 会让 LLM 失败时 silent drop

---

## 七、防御性编码建议

1. **写 skill 之前**先 `python3 -c "import skillopt_sleep; print(skillopt_sleep.__file__)"` 确认仓库路径
2. **跑 cycle 之前**先 `python -m skillopt_sleep.experiments.run_experiment --persona researcher --assert-improves` 验证 engine
3. **写 cron 之后**立刻 `cronjob run <id>` 手动跑一次
4. **改 jobs.json 之后** `cp jobs.json jobs.json.bak.<ts>` 备份
5. **skill 文档列出的 support files 必须真存在** — 占位文件会让 agent 扑空
6. **永远不要**在 terminal 命令里 inline 写 API key（用 Python 读取 + subprocess env 注入）
7. **DeepSeek key** 用 `rstrip()` 去除尾部 `\n`，不要用 shell `export KEY=$(grep ...)`
