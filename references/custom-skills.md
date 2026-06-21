# 自建/修改 Skill 清单

> 数据来源：`~/.hermes/skills/` 目录扫描
> 提取时间：2026-06-21
> 以下 skill 为我们自建或深度修改的版本

---

## Skill 列表

| Skill | 大小 | 最后修改时间 | 说明 |
|-------|------|-------------|------|
| **auxiliary-model-diagnosis** | 35,705 bytes | 2026-06-20 13:36 | 辅助模型诊断 — 12 个 auxiliary sub-task 的 provider 路由、凭证验证、模型特定踩坑（含 model-网关伪装陷阱） |
| **ima-skill** | 24,853 bytes | 2026-06-20 13:08 | IMA 知识库集成 — 飞书/微信笔记管理、知识沉淀、免费资源灌入 |
| **skillopt-integration** | 26,899 bytes | 2026-06-18 02:01 | SkillOpt-Sleep 集成 — 端到端 PoC 实测 17 条踩坑记录 + cron 集成 |
| **llm-usage-analysis** | 12,701 bytes | 2026-06-15 02:53 | LLM 用量分析 — Token 消耗统计、成本分析 |
| **public-figure-investigation** | 11,063 bytes | 2026-06-07 16:01 | 公众人物调查 — 信息搜集与结构化输出 |
| **gateway-restart-vs-reload** | 8,849 bytes | 2026-06-18 06:24 | Gateway 重启 vs 重载 — SIGUSR1 与 systemd 全重启的区别，平台连接问题诊断 |
| **github-pr-contributions** | 8,348 bytes | 2026-06-06 11:33 | GitHub PR 贡献 — PR 管理与贡献统计 |
| **wiki-automation** | 3,467 bytes | 2026-05-09 09:08 | Wiki 自动化 — 飞书文档/知识库自动化操作 |
| **agent-reach** | 4,960 bytes | 2026-06-20 06:10 | Agent Reach — 多渠道消息触达能力 |

---

## 详细信息

### auxiliary-model-diagnosis (v1.2.0)
- **作者**：Mimir
- **依赖**：`references/verification-methodology.md`, `references/auxiliary-thinking-block-pollution.md`, `references/longcat-thinking-test.md`
- **覆盖**：12 个 auxiliary sub-task 的诊断流程
- **踩坑记录**：
  - `openrouter/free` vision 404 → GLM-4V fallback
  - `deepseek-v4-flash` reasoning mode → content 为空
  - `Api.openmodel.ai` 协议不对称 → 必须用 `anthropic_messages`
  - `Api.qnaigc.com` model channel mismatch → 某些模型无通道

### ima-skill
- **功能**：IMA 知识库 API 集成
- **子模块**：`ima_api.cjs`（Node.js API 客户端）
- **能力**：笔记本/笔记/文件夹 CRUD，知识灌入

### skillopt-integration
- **功能**：SkillOpt-Sleep 自动优化框架集成
- **踩坑记录**：17 条（DeepSeek key 尾部 `\n`、reasoning-only 模型、get_backend 硬编码、循环论证等）
- **依赖**：`skillopt_sleep` Python 包

### gateway-restart-vs-reload
- **作者**：skill-evolution (evolution_round: 1)
- **核心发现**：
  - `hermes gateway restart` = SIGUSR1 → 重载配置但不重建平台连接
  - 平台连接断开时必须用 `systemctl --user stop && start` 全重启
  - `hermes gateway restart` 确实会 spawn 新 PID（不是进程内重载）

### llm-usage-analysis
- **功能**：分析 LLM 使用量、Token 消耗、成本估算
- **数据源**：`agent.log`, `bounty_tokens.csv`

### public-figure-investigation
- **功能**：公众人物信息调查与结构化输出

### github-pr-contributions
- **功能**：GitHub PR 管理与贡献统计

### wiki-automation
- **功能**：飞书文档/知识库自动化操作

### agent-reach
- **功能**：Agent 多渠道消息触达能力
