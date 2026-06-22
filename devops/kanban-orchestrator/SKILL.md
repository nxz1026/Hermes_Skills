---
name: kanban-orchestrator
description: Decomposition playbook + specialist-roster conventions + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role. Also covers AI Loop Coder→Auditor dependency chain pattern (2026-06-21).
---
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
    related_skills: [kanban-worker, kanban-reasonix-lane, cron-workflow, auditor, self-reflection]
---

# Kanban Orchestrator — Decomposition Playbook

> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **If no specialist fits, ask the user which profile to create.** Do not default to doing it yourself under "close enough."
- **Decompose, route, and summarize — that's the whole job.**

## The standard specialist roster (convention)

Unless the user's setup has customized profiles, assume these exist. Adjust to whatever the user actually has — ask if you're unsure.

| Profile | Does | Typical workspace |
|---|---|---|---|
| `researcher` | Reads sources, gathers facts, writes findings | `scratch` |
| `analyst` | Synthesizes, ranks, de-dupes. Consumes multiple `researcher` outputs | `scratch` |
| `writer` | Drafts prose in the user's voice | `scratch` or `dir:` into their Obsidian vault |
| `auditor` | **Code audit specialist** — 6-dimension audit (Security/Correctness/Quality/Testing/Integration/Compliance) with P0/P1/P2 rating. Read-only, never modifies code. Loads `auditor` skill. | `scratch` or `worktree` |
| `reasonix` | **Coding specialist only** — write code, refactor, code review, mechanical migration. DeepSeek-powered. | `scratch` or `worktree` |
| `auditor` | **Code audit specialist** — 6-dimension audit (Security/Correctness/Quality/Testing/Integration/Compliance) with P0/P1/P2 rating. Read-only, never modifies code. Loads `auditor` skill. | `scratch` or `worktree` |
| `backend-eng` | Writes server-side code | `worktree` |
| `frontend-eng` | Writes client-side code | `worktree` |
| `ops` | Runs scripts, manages services, handles deployments | `dir:` into ops scripts repo |
| `pm` | Writes specs, acceptance criteria | `scratch` |

> ⚠️ **`reasonix` is a coding-only profile.** Never assign investigation, analysis, research, or system diagnosis tasks to it. Those go to the default/generalist profile.

### Profile Routing Convention（聂聃专用 AI Loop）

This user has three active kanban profiles forming an **AI Loop 流水线**：

| Profile | Role | Assigned tasks | Provider | Model |
|---------|------|---------------|----------|-------|
| `default` | Planner（老蜜） | 分析、拆任务、建卡、终审、会话交互 | stepfun | step-router-v1 |
| `reasonix` | Coder（编码执行） | 写代码、重构、代码审查、>50 行代码任务 | custom:Api.longcat.chat | LongCat-2.0-Preview |
| `auditor` | Auditor（代码审计） | 6 维度审计 Coder 产出，只审不改，P0/P1/P2 评级 | deepseek（官方） | deepseek-v4-flash |

**关键规则**：
- **模型隔离**：Coder（LongCat）和 Auditor（DeepSeek 官方）必须用不同模型，审计才有制衡意义
- **do NOT assign analysis/investigation tasks to `reasonix`** — it's a coding specialist only
- **do NOT assign code reviews to `default`** unless the task is architecture-level reasoning without code changes
- **Auditor 自动通知**：Auditor 完成审计后，通过 `kanban notify-subscribe` 通知 Planner（老蜜）
- 如果不确定，default to `default`（老蜜）并让 dispatcher 引导

**AI Loop 编码流水线**：
```
Planner（default）→ 拆任务 → 建 Coder 卡（reasonix）
    → Coder 完成 → 自动建 Auditor 卡（auditor，parent=Coder）
        → Auditor 审计 → 通知 Planner → 老蜜终审
```
详见 `references/ai-loop-pipeline.md`。
Key convention: **do NOT assign analysis/investigation tasks to `reasonix`**. The reasonix profile is strictly for code-related work. Similarly, do NOT assign code reviews to `default` unless the task is architecture-level reasoning without code changes. If uncertain, default to `default` and let the dispatcher guide. Explicit `--assignee reasonix` on `kanban create` for any coding task.

## Decomposition playbook

### Step 1 — Understand the goal

Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

### Step 2 — Sketch the task graph

Before creating anything, draft the graph out loud (in your response to the user). Example for "Analyze whether we should migrate to Postgres":

```
T1  researcher        research: Postgres cost vs current
T2  researcher        research: Postgres performance vs current
T3  analyst           synthesize migration recommendation       parents: T1, T2
T4  writer            draft decision memo                       parents: T3
```

Show this to the user. Let them correct it before you create anything.

### Step 3 — Create tasks and link

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="researcher",
    body="Compare estimated infrastructure costs, migration costs, and ongoing ops costs over a 3-year window. Sources: AWS/GCP pricing, team time estimates, current Postgres bills from peers.",
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="researcher",
    body="Compare query latency, throughput, and scaling characteristics at our expected data volume (~500GB, 10k QPS peak). Sources: benchmark papers, public case studies, pgbench results if easy.",
)["task_id"]

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="analyst",
    body="Read the findings from T1 (cost) and T2 (performance). Produce a 1-page recommendation with explicit trade-offs and a go/no-go call.",
    parents=[t1, t2],
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="writer",
    body="Turn the analyst's recommendation into a 2-page memo for the CTO. Match the tone of previous decision memos in the team's knowledge base.",
    parents=[t3],
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed; the dispatcher and dependency engine handle it.

### Step 4 — Complete your own task

If you were spawned as a task yourself (e.g. `planner` profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 researchers parallel, 1 analyst on their outputs, 1 writer on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "researcher", "parents": []},
            "T2": {"assignee": "researcher", "parents": []},
            "T3": {"assignee": "analyst", "parents": ["T1", "T2"]},
            "T4": {"assignee": "writer", "parents": ["T3"]},
        },
    },
)
```

### Step 5 — Report back to the user

Tell them what you created in plain prose:

> I've queued 4 tasks:
> - **T1** (researcher): cost comparison
> - **T2** (researcher): performance comparison, in parallel with T1
> - **T3** (analyst): synthesizes T1 + T2 into a recommendation
> - **T4** (writer): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

### 批量归档（清理已完成任务）

```bash
# 归档单个任务
hermes kanban archive <task_id>

# 归档多个任务（空格分隔，所有 task_id 写到一行）
hermes kanban archive t_xxxxxxx t_yyyyyyy t_zzzzzzz

# 彻底清理已归档任务的 workspace
hermes kanban gc
```

> ⚠️ `archive` 是唯一删除方式——Kanban 没有 `delete` 命令。归档后运行 `gc` 释放磁盘空间。

`--parents` flag does not exist on `kanban create`. Attempting to pass it causes Hermes CLI to misparse and error.

**Correct sequence:**
```bash
# 1. Create tasks first (no parent flag)
hermes kanban create "Task A" --assignee "researcher"
# → Created t_aaaaaaa (ready, assignee=researcher)

hermes kanban create "Task B depends on A" --assignee "analyst"
# → Created t_bbbbbbb (ready, assignee=analyst)

# 2. Link AFTER creation (separate command)
hermes kanban link t_aaaaaaa t_bbbbbbb
# → Linked t_aaaaaaa -> t_bbbbbbb

# 3. Verify
hermes kanban show t_bbbbbbb
```

**Common mistake:** Running `hermes kanban create ... --parents t_aaa,t_bbb` which causes CLI to error out with "unrecognized arguments".

### Common patterns

**Fan-out + fan-in (research → synthesize):** N `researcher` tasks with no parents, one `analyst` task with all of them as parents.

**Pipeline with gates:** `pm → backend-eng → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.

**Same-profile queue:** 50 tasks, all assigned to `translator`, no dependencies between them. Dispatcher serializes — translator processes them in priority order, accumulating experience in their own memory.

**Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.

**AI Loop 编码流水线（Planner → Coder → Auditor）：** 见 `references/ai-loop-pipeline.md`。适用于所有编码任务：Coder 卡（assignee=reasonix）→ Auditor 卡（assignee=auditor，parent=Coder 卡）→ 老蜜终审。

## Pitfalls

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

**Before decomposing a planning task, VERIFY the raw data.** If the task involves reading from a source (calendar, docs, logs), claim the task, verify the data, THEN plan. A plan based on unverified data may be completely wrong.

**Example trap:** Reading task labels — always read the task body's actual content, not just the label.

### Bulk task creation via Python (execute_code or terminal)

For 20+ tasks, write a Python script and run it via `execute_code` (faster, no 60s terminal timeout). The hermes binary path differs by environment:

```python
import subprocess

# execute_code sandbox: use this path
KANBAN = "/root/.hermes/hermes-agent/venv/bin/hermes"

# terminal: discover with which
# KANBAN = subprocess.run(["which", "hermes"], capture_output=True).stdout.decode().strip()

tasks = [
    ("Task title", "assignee_profile", "Task body/description"),
    # ...
]

for title, assignee, body in tasks:
    r = subprocess.run(
        [KANBAN, "kanban", "create", title, "--assignee", assignee],
        input=body.encode(), capture_output=True, timeout=30
    )
    print(r.stdout.decode().strip())
```

Key discovery: `--assignee` flag works on `kanban create`; stdin provides the body. Do NOT use `--parents` flag (doesn't exist —会导致CLI解析错误). Instead, create tasks then use `hermes kanban link <parent_id> <child_id>`.

## 批量创建场景的 exec_strategy

When creating a study plan with 30+ calendar events or kanban tasks:
1. Write a Python script to `/tmp/`
2. Use `execute_code` (no 60s terminal timeout) rather than `terminal`
3. Pass `capture_output=True` + explicit timeouts on subprocess calls
4. Print a progress counter every N items so you can verify partial success

## Profile routing conventions (real-world)

When routing tasks to actual configured profiles, follow this mapping from generic roles to real profiles. The generalist/default profile can handle anything; specialized profiles have clear scope limits.

| Real profile | Equiv role | Scope | Model note |
|---|---|---|---|
| `default` | generalist/full-stack | Any task: research, analysis, investigation, coding, writing | Full Hermes toolchain |
| `reasonix` | coding specialist | Write code, refactor, code review, mechanical migration, documentation **only** | DeepSeek official (reliable, no 429) |

**Critical rules:**
- **DO NOT assign investigation/analysis/research tasks to `reasonix`** — it's a coding specialist only. Log investigation, anomaly analysis, market research → `default`.
- **DO NOT assign tasks that need web search, browser, multi-tool chains to `reasonix`** — `default` has the full toolchain.
- **DO NOT assign Coder tasks that need `kanban_complete` to `reasonix`**（2026-06-22 实战）—— reasonix/LongCat 跑脚本没问题，但不会调 `kanban_complete` 回传结果，导致 protocol_violation。需要 kanban 协议的任务用 `default`。
- If a coding task also needs investigation (e.g. "find the root cause of this bug in logs, then fix it"), decompose: investigation subtask → `default`, fix subtask → `reasonix`.
- If `reasonix` hits 429 rate limits repeatedly, reclaim and reassign to `default` with a note about the provider limitation.

## AI Loop 模式：Coder → Auditor 依赖链（2026-06-21 实战）

### 模式：编码任务 + 自动审计

```
Coder 卡（assignee=reasonix）
  └── link → Auditor 卡（assignee=auditor, status=todo）
              └── Coder 完成后自动 promoted → running
```

**创建步骤**：
1. `kanban create "任务标题" --assignee reasonix --body "..."` → 得到 t_aaa
2. `kanban create "审计: 任务标题" --assignee auditor --body "..."` → 得到 t_bbb
3. `kanban link t_aaa t_bbb` → 建立依赖

**关键**：Auditor 卡的 `parents` 会自动从 Coder 完成事件中收到 `promoted`，然后被 dispatcher 派发。

### 飞书通知：Planner 订阅 Auditor 卡

Auditor 完成审计后，Planner（用户）需要收到通知。由于 kanban worker 的 toolsets 受限（reasonix/auditor 默认不含 `messaging`），**不能直接发飞书**。

**解法**：Cron prompt 里用 `kanban notify-subscribe` 提前订阅：
```bash
hermes kanban notify-subscribe t_auditor_task_id \
  --platform feishu \
  --chat-id <user_chat_id> \
  --notifier-profile default
```

`--notifier-profile default` 用有完整工具链的 profile 发送通知。

### 工具集陷阱（2026-06-21 教训）

| Profile | 默认工具集 | 能发飞书？ |
|---------|-----------|-----------|
| default（gateway running） | 全量 | ✅ |
| reasonix | terminal + file | ❌ |
| auditor | terminal + file | ❌ |

**规则**：需要发飞书/消息的任务，必须由 default profile 或指定 `--notifier-profile default` 发送。不要在 Coder/Auditor 的 prompt 里写"发飞书通知"，它们做不到。

## Cron + Kanban integration

Cron jobs (scheduled detection) and Kanban (async execution) are complementary:

### Pattern 1: Cron triggers → Kanban executes (recommended)

```
cron runs (detection phase):
  → reads logs, scans system, collects data
  → if issue found: kanban_create("handle X", assignee=correct-profile)
  → also pushes its normal report to user (both paths active)

kanban dispatcher (within 60s):
  → spawns worker on correct profile
  → worker investigates, fixes, produces output
  → kanban_complete results landed
```

**When to use:** Cron detects anomalies (log spikes, errors, data changes) that need deeper investigation or action. The cron's LLM-driven report goes to the user immediately; the kanban task runs asynchronously in parallel.

**Example** (from log-daily-scan):
```bash
# Inside cron prompt, Step 6:
if [P0] or [P1] items exist:
    hermes kanban create "调查日志异常: <summary>" \
      --assignee default \
      --body "$(cat /tmp/issues.txt)"
```

### Pattern 2: Cron produces data → Kanban consumes

```
cron → writes artifact to /tmp/daily_data.json
     → kanban_create "analyze daily data" --workspace dir:/tmp

worker → reads /tmp/daily_data.json → analyzes → kanban_complete
```

**When to use:** Cron generates artifacts or snapshots that need post-processing requiring LLM reasoning.

### Pattern 3: Kanban creates Cron (rare)

Worker discovers "this needs daily monitoring" → `cronjob(action='create')` to schedule. Less common.

### Real-world verification (2026-06-20)

The cron→kanban integration was tested end-to-end with `log-daily-scan`:

1. `hermes cron run 014b2b65edd5` triggered a manual scan
2. Agent scanned logs, found **P1 SSH brute-force** (7160 failed passwords/24h, 92 IPs)
3. Step 6 executed: `kanban create "调查日志异常: SSH brute-force 7160次/24h，Log_daily_status.py 盲区" --assignee default`
4. Dispatcher spawned a `default` profile worker investigating
5. Full scan report (with `[KANBAN] 已派调查任务：t_7b849a5a` line) delivered to Feishu in parallel

**Key takeaway:** Both delivery paths worked simultaneously. The kanban task is truly additive — it doesn't block or replace the cron report.

### Integration checklist

- [ ] Cron prompt includes final step: detect condition → `kanban_create`
- [ ] Assignee matches task type (coding→reasonix, investigation→default)
- [ ] `enabled_toolsets` on cron job includes `terminal` (needed for `hermes kanban create`)
- [ ] Report to user still fires normally — kanban task is additive, not a replacement
- [ ] Consider failure modes: what if kanban create fails (network, permissions)? Cron should still push its report.

## Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.

## 不应使用本 skill 的场景

- 单一简单任务（一个工具调用能解决）→ 直接 `delegate_task` 或自己回答
- 用户明确说"别建看板，直接做"→ 尊重 override
- 任务不需要多角色协作 → 一个 profile 干到底
- 临时一次性查询（"帮我查个东西"）→ 不需要持久化

## 常见借口与反驳（Rationalizations）

| 借口 | 现实 |
|------|------|
| "这个任务我自己就能做，不用建卡" | 能 ≠ 应该。建卡提供持久化、可审计、可恢复的执行轨迹。自己做失去所有这些。 |
| "建 Coder 卡就行，Auditor 卡跳过" | 无审计的代码 = 盲飞。Coder 和 Auditor 的模型隔离是 AI Loop 的制衡基础。 |
| "任务太简单，不需要 Auditor" | 简单 ≠ 正确。单行改动可以引入 bug。Auditor 的 6 维度不因行数打折。 |
| "先建卡，等会再设依赖" | 依赖关系是任务图的核心。事后补链容易漏、容易错，必须在建卡时就设好。 |
| "reassign 就行，不用重建" | Worker 的上下文不会自动迁移。如果问题是 prompt 设计缺陷，reassign 换模型也修不好。 |
| "用 `--parents` 参数一步到位" | `--parents` 不存在于 `kanban create`。先建卡再 `kanban link` 是唯一正确路径。 |
| "Cron 报告已经发了，不用再建 Kanban 任务" | Cron 报告和 Kanban 任务是互补的。Cron 报告是通知，Kanban 任务是执行。两者并行不冲突。 |

## 红旗信号（Red Flags）

- 自己动手执行而不建卡（"anti-temptation rules" 违规）
- 把分析/调查任务分配给 reasonix（reasonix 是 coding-only）
- 用 `--parents` 参数建卡（CLI 会报 unrecognized arguments）
- Coder 和 Auditor 用同一个模型（失去制衡）
- Auditor 卡未设 `notify-subscribe`（Planner 收不到审计完成通知）
- 批量建卡超过 20 个不用 Python 脚本（逐个 terminal 太慢）
- 图依赖关系未向用户展示就直接建卡（应该先展示，等确认）

## 互动与其他 Skill

- **`auditor`**：本 skill 的核心下游。Auditor 是 AI Loop 的审计闸门，通过 Coder→Auditor 依赖链与本 skill 集成。
- **`resume-ai-loop`**：本 skill 的典型使用者。简历自动更新流水线完全依赖 Kanban 调度。
- **`kanban-worker`**：Worker 的生命周期规则。Orchestrator 了解 worker 的约束才能正确路由。
- **`self-reflection`**：反思引擎扫 Kanban 流水线历史，提取路由错误（如任务错配 profile），反馈到本 skill 的 routing conventions。
- **`cron-workflow`**：Cron→Kanban 集成的三种模式（cron 触发 kanban / cron 产数据 kanban 消费 / kanban 建 cron）。

## 验证清单（Verification）

每次编排完成后逐项确认：

- [ ] 任务图已向用户展示，用户已确认（Step 2）
- [ ] 所有任务都通过 `kanban create` 创建（未手动执行）
- [ ] 依赖关系通过 `kanban link` 设置（未使用 `--parents`）
- [ ] 编码任务分配给 reasonix；分析/调查任务分配给 default
- [ ] Coder 和 Auditor 任务使用了不同模型（LongCat vs DeepSeek 官方）
- [ ] Auditor 卡已设 `notify-subscribe`（通知 Planner）
- [ ] 批量任务（>20 个）使用了 Python 脚本而非逐个 terminal
- [ ] 任务完成后已 `kanban_complete` 回传 summary
- [ ] 未尝试自己执行子任务（anti-temptation rules 合规）
