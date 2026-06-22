# AI Loop Coder→Auditor 依赖链模式（2026-06-21 实战）

## 模式定义

编码任务通过 Kanban 依赖链实现 Coder→Auditor 自动流转：

```
Coder 卡（reasonix）→ 写代码 → complete
       ↓
Auditor 卡（auditor，parent=Coder卡）→ 审计 → complete
       ↓
kanban notify-subscribe → 飞书通知 Planner
```

## 创建步骤

```bash
# 1. 创建 Coder 卡
hermes kanban create "任务标题" --assignee reasonix --body "..."

# 2. 创建 Auditor 卡
hermes kanban create "审计: 任务标题" --assignee auditor --body "..."

# 3. 建立依赖
hermes kanban link <coder_task_id> <auditor_task_id>
```

Auditor 卡的 `parents` 会自动从 Coder 完成事件中收到 `promoted`，然后被 dispatcher 派发。

## 工具集陷阱

| Profile | 默认工具集 | 能发飞书？ |
|---------|-----------|-----------|
| default（gateway running） | 全量 | ✅ |
| reasonix | terminal + file | ❌ |
| auditor | terminal + file | ❌ |

**规则**：需要发飞书/消息的任务，必须由 default profile 或指定 `--notifier-profile default` 发送。

## 飞书通知方案

```bash
hermes kanban notify-subscribe <auditor_task_id> \
  --platform feishu \
  --chat-id <user_chat_id> \
  --notifier-profile default
```

`--notifier-profile default` 确保订阅者有 messaging 工具。

## 模型隔离要求

| 角色 | Profile | 模型 | 提供方 |
|------|---------|------|--------|
| Planner | default | step-router-v1 | stepfun |
| Coder | reasonix | LongCat-2.0-Preview | Api.longcat.chat |
| Auditor | auditor | deepseek-v4-flash | DeepSeek 官方 |

**原则**：Coder 和 Auditor 必须用不同模型，才有制衡意义。同一模型做编码和审查等于自审。
