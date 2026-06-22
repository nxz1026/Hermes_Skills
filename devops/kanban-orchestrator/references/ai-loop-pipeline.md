# AI Loop 编码流水线（2026-06-21 落地）

## 架构

```
用户需求
  │
  ▼
Planner（老蜜，default profile）
  │ 分解任务，建 Kanban 卡
  │
  ├─▶ Coder 卡 → assignee=reasonix
  │     │  LongCat-2.0-Preview (custom:Api.longcat.chat)
  │     │  >50 行代码走 reasonix
  │     │  简单单步老蜜直接干
  │     └─ 完成 → 自动触发
  │
  └─▶ Auditor 卡 → assignee=auditor, parent=Coder卡
        │  deepseek-v4-flash（官方版，与 Coder 模型隔离）
        │  加载 auditor skill
        │  6 维度审计（安全/正确性/质量/测试/集成/合规）
        │  P0/P1/P2 评级
        │  只审不改，输出固定表格
        └─ 报告回传老蜜 → 终审
```

## 关键规则

1. **>50 行代码 → reasonix**：预估超过 50 行的代码任务派给 reasonix，老蜜只审不写
2. **Coder 完成后自动触发 Auditor**：Kanban 依赖链，Coder 卡 done → Auditor 卡 ready
3. **Auditor 只审不改**：read-only，禁止 git push，发现 P0/P1 驳回
4. **模型隔离**：Coder（LongCat）和 Auditor（DeepSeek 官方）必须用不同模型
5. **delegate_task 不带 acp_command**：reasonix 不支持 ACP 协议
6. **reasonix 不接调查任务**：只写代码，不搞分析/研究/诊断

## 看板命令

```bash
# Coder 卡
hermes kanban create "实现 XXX 功能" --assignee reasonix

# Auditor 卡（依赖 Coder 卡）
hermes kanban create "审计 XXX 实现" --assignee auditor
hermes kanban link <coder_id> <auditor_id>

# 查看状态
hermes kanban show <id>
```

## 关联 Skill

- `auditor` — 审计角色定义（6 维度 + P0/P1/P2）
- `self-reflection` — 自我反思（session 后自动提取教训，三通道扫描）
- `kanban-orchestrator` — 看板编排
- `kanban-worker` — 看板工人
- `world-cup-predict` — 世界杯预测（含自审闭环）

## 相关 Profile

| Profile | 配置 | 用途 | 模型 |
|---------|------|------|------|
| `auditor` | `~/.hermes/profiles/auditor/` | 代码审计，SOUL.md 含审计长人格 | deepseek-v4-flash |
| `reasonix` | `~/.hermes/profiles/reasonix/` | 编码专用，SOUL.md 含首席工程师人格 | LongCat-2.0-Preview |
| `default` | 已有 | 全工具链，调查/分析/派发 | step-router-v1 |
