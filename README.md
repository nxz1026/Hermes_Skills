# Hermes Skills

（肉山）的 Hermes Agent 自建 Skill 集合。

## 目录结构

```
Hermes_Skills/
  productivity/
    resume-ai-loop/       # 简历自动更新 AI Loop（Planner→Coder→Auditor）
    world-cup-predict/    # 2026 世界杯预测 + 自动回填 + 复盘
  devops/
    kanban-orchestrator/  # Kanban 多 Agent 编排，AI Loop 依赖链
```

## AI Loop 流水线

```
Planner(default) → Coder(reasonix/LongCat) → Auditor(auditor/DeepSeek) → 老蜜终审
```

- **resume-ai-loop**：每天 00:40 BJT 自动扫描 GitHub + 知识沉淀 → 对比简历 → 自动更新飞书文档
- **world-cup-predict**：每天 10:30 BJT 预测 + 回填 + 自审，Poisson 比分分布
- **kanban-orchestrator**：任务拆解、角色路由、Coder→Auditor 依赖链

## 硬链接

所有文件通过硬链接与 `~/.hermes/skills/` 同步。修改原文件后，repo 自动同步，只需 `git commit` 即可。
