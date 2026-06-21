# LongCat Feedback — free-ai-resources 集成

**日期**：2026-06-21  
**任务**：T4 集成 free-ai-resources skill 并创建 cron

---

## 1. 已完成操作

| 步骤 | 状态 | 说明 |
|------|------|------|
| 软链接 skill 到 ~/.hermes/skills/ | ✅ 完成 | `~/.hermes/skills/free-ai-resources` → `/root/2026workplace/Hermes_Skills/skills/free-ai-resources` |
| 创建 cron 任务 | ✅ 完成 | Job ID: `3a5d2ea9b778`，Schedule: `30 19 * * *`，Deliver: `feishu` |
| 脚本 dry-run 验证 | ⚠️ 部分通过 | 脚本本身无报错（exit 0），但所有搜索请求失败 |

---

## 2. 遇到的问题

### 问题 1：Jina 搜索 API 返回 403 Forbidden

**现象**：
```
WARN: Jina 搜索请求失败: HTTP Error 403: Forbidden
```

**影响**：
- `free_ai_resources.py --dry-run` 执行后 fetch 阶段获取 0 条结果
- pipeline 在 parse 阶段因无输入而提前终止
- cron 每日运行时将无法爬取任何新资源

**根因推测**：
- Jina API key 未配置或已过期
- `~/.hermes/config.yaml` 中 `web.search_backend` 或相关 Jina 配置缺失
- 网络层对 Jina API 的访问被限制

**建议修复**：
1. 检查 `~/.hermes/config.yaml` 中 `web` 部分的 Jina API key 配置
2. 确认 Tavily 或其他搜索 backend 的可用性作为 fallback
3. 若使用 Jina，需确保 `mcp_jina_search_web` 的认证信息已正确注入 Hermes 环境

---

## 3. Cron 任务详情

- **Job ID**：`3a5d2ea9b778`
- **名称**：🆕 免费资源扫描
- **Schedule**：`30 19 * * *`（每天 19:30 BJT）
- **Provider**：`custom:Api.longcat.chat`
- **Model**：`LongCat-2.0-Preview`
- **Skills**：`free-ai-resources`
- **Enabled Toolsets**：`["web", "terminal", "file"]`
- **Deliver**：`feishu`
- **Prompt**：加载 free-ai-resources skill，按 SKILL.md 执行爬取→解析→去重→分类→推送流程
- **Next Run**：`2026-06-21T19:30:00+00:00`

---

## 4. 后续行动

- [ ] 修复 Jina API 403 问题，确保 cron 能正常爬取
- [ ] 验证 cron 首次执行时飞书推送和 IMA 同步是否正常
- [ ] 考虑添加 search backend fallback 机制
