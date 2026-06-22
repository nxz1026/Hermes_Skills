---
name: resume-ai-loop
description: 简历迭代 AI Loop —— 从 GitHub 项目更新 + Hermes 知识沉淀到飞书文档修改的全自动闭环流水线。触发词：更新简历、迭代简历、简历修改、GitHub 项目更新了。
---

# 简历迭代 AI Loop

> 全自动闭环：搜集 → 分析 → 改文档 → 审计 → 自修复 → 重试 → 通知。用户只收最终结果。

## 核心原则

1. **全自动，不打断用户**：Phase 1/2/3 全部自主决策，不改完不吭声
2. **真 Loop，不是审批流**：Auditor 驳回后自动分析根因、修复、重试，最多 3 轮
3. **只写有深度的东西**：知识沉淀只取架构决策/自研算法/复杂系统设计，不写模型对比和环境配置
4. **安全第一**：每次改动前自动备份快照，P0 驳回自动回滚
5. **手动修复走本地**：用户主动要求修复 Auditor 发现的问题时，不直接改飞书文档——保存 MD 到 `/root/resume/`，让用户自己审阅后决定是否同步到飞书

## 流水线总览

```
Phase 1: 信息收集
  ├── 1a. 拉 GitHub 最新项目
  ├── 1b. 读飞书现有简历
  ├── 1c. 读 Hermes 知识沉淀（最近 7 天）
  └── 1d. 知识沉淀质量门过滤

Phase 2: 自主分析 & 决策
  ├── 差距分析（GitHub 实际 vs 简历现状 vs 知识沉淀）
  ├── 决定更新哪些章节
  └── 生成新版内容

Phase 3: AI Loop 执行（最多 3 轮）
  ├── Coder 卡（reasonix/LongCat）：写脚本改飞书文档
  ├── Auditor 卡（auditor/deepseek）：审计 Coder 产出
  └── 驳回 → 根因分析 → 自修复 → 重建 Coder 卡

Phase 4: 通知
  └── 通过 → 飞书推送简短通知
```

## 关键常量

```
飞书简历文件夹: Z0EffK7OIltTK8ds0DOcTYmkndg
原始简历子文件夹: Ejt7fVYNdlMW4hdMuC9cJJ0Anzd
主简历 docx ID: YC6mdN1dDowEqvxqxykc33h7n3c
社工简历 docx ID: BVCid6v9Yo3qM6xDSLmcVUXcnrf
本地简历目录: /root/resume/  (手动修复时 MD 输出目录)
GitHub: nxz1026
知识沉淀目录: ~/.hermes/data/hermes_knowledge/
HERMES_BIN: /usr/local/lib/hermes-agent/venv/bin/hermes
MAX_LOOP_ROUNDS: 3
```

---

## Phase 1: 信息收集

### 1a. 拉 GitHub 项目（含 fork 甄别）

```bash
# 拉所有仓库
gh repo list nxz1026 --limit 30 --json name,isFork,parent,description,updatedAt,pushedAt,primaryLanguage,url
```

然后对每个 fork 仓库，检查是否有实际改动（commits ahead of upstream）：

```bash
# 对每个 isFork=true 的仓库：
PARENT=$(gh api "repos/nxz1026/$REPO" --jq '.parent.full_name')
FBR=$(gh api "repos/nxz1026/$REPO" --jq '.default_branch')
PBR=$(gh api "repos/$PARENT" --jq '.default_branch')
AHEAD=$(gh api "repos/$PARENT/compare/$PBR...nxz1026:$FBR" --jq '.ahead_by')
```

**甄别规则**：
- `ahead > 0`：fork 有实际改动，纳入简历候选
- `ahead == 0`（identical 或 behind）：纯 fork，未做任何修改，**排除**——不算用户的项目
- 原创仓库（isFork=false）：全部纳入

策略：按 pushedAt 排序，关注最近 30 天内有推送的项目。fork 只有 ahead > 0 才算。

### 1b. 读飞书简历

```bash
export $(grep -E '^FEISHU_APP_(ID|SECRET)=' /root/.hermes/.env | xargs)
python3 /root/.hermes/skills/community/feishu-lark-agent/feishu.py doc get --id YC6mdN1dDowEqvxqxykc33h7n3c
```

### 1c. 读 Hermes 知识沉淀

读取最近 7 天的知识沉淀文件：

```bash
ls -t ~/.hermes/data/hermes_knowledge/*.md | head -7
```

### 1d. 知识沉淀质量门过滤

**必须同时满足以下条件才写入简历**：

- 信号强度：内容包含「架构决策」「自研算法」「复杂系统」「可复用模式」「自动化闭环」中至少 2 个维度
- 工程深度：不是一次性的环境配置、不是模型对比测试、不是简单 bug 修复
- 可展示性：对外行（HR/技术负责人）能讲清楚「做了什么、为什么难、效果如何」

**✅ 通过示例**：
- AI Loop 设计（Planner→Coder→Auditor 闭环）：架构决策 + 自动化闭环
- 证据打分引擎（5 维 + 3 场景 + 纯规则）：自研算法 + 可复用模式
- 多模型交叉验证机制（GLM-4V/DeepSeek/Qwen-VL 三方独立抽取）：复杂系统
- 飞书全自动化（文档/日历/云盘/消息 API 统一编排）：可复用模式 + 自动化闭环

**❌ 拒绝示例**：
- 模型基准测试对比（DeepSeek vs LongCat 延迟）：一次性对比，无工程深度
- 环境配置记录（pip install、apt update）：运维操作，无可展示性
- 简单 bug 修复（修了个编码问题）：无架构价值
- LLM 限流/欠费处理：临时性上游问题

**过滤后输出**：只保留通过质量门的条目，作为简历更新的候选内容。

---

## Phase 2: 自主分析 & 决策

### 分析维度

1. **GitHub vs 简历**：哪些项目在简历里没写或写得不够
2. **简历 vs GitHub 实际**：简历里写的功能描述是否准确、是否遗漏关键特性
3. **知识沉淀 vs 简历**：最近 7 天的工程深度事件是否值得加入「AI 系统搭建能力」或「核心竞争力」章节

### 决策规则

- 与求职方向（医疗 AI / 医工结合 / 项目经理）无关的项目 → 跳过
- 项目有实质性更新（新功能/新架构/新模块）→ 更新对应章节
- 知识沉淀有高质量条目 → 决定插入哪个章节
- 无任何变化 → 跳过本次运行，不通知

### 输出

生成新版简历内容（markdown 格式），标注改动点。

---

## Phase 3: AI Loop 执行

### 3.0 自动备份

Coder 动手前，先备份当前文档快照：

```bash
export $(grep -E '^FEISHU_APP_(ID|SECRET)=' /root/.hermes/.env | xargs)
python3 /root/.hermes/skills/community/feishu-lark-agent/feishu.py doc get --id YC6mdN1dDowEqvxqxykc33h7n3c > /tmp/resume_backup_$(date +%Y%m%d_%H%M%S).md
```

### 3.1 创建 Kanban 任务

```bash
# 1. Coder 卡
hermes kanban create "更新简历: <章节名>" --assignee reasonix
# body: 完整更新指令（文档 ID、定位方式、旧内容、新内容、执行步骤）

# 2. Auditor 卡（依赖 Coder）
hermes kanban create "审计: 简历 <章节名>" --assignee auditor

# 3. 链接
hermes kanban link <coder_id> <auditor_id>

# 4. 订阅通知
hermes kanban notify-subscribe <auditor_id> \
  --platform feishu \
  --chat-id oc_03ed3a1169febbd1e9348945ffd24689 \
  --notifier-profile default
```

### 3.2 Loop 循环（核心）

```
Round N (1-3):
  ├── 等待 Auditor 完成
  ├── 读 Auditor 报告
  ├── 判断：
  │   ├── 通过 / 有条件通过 (P2) → 退出循环，进入 Phase 4
  │   └── 驳回 (P0/P1) → 分析根因 → 自修复 → 重建 Coder 卡 → Round N+1
  └── Round 3 仍驳回 → 通知用户 + 自动回滚
```

### 3.3 根因分析 & 自修复

Auditor 驳回时，根据驳回原因分类处理：

| 驳回原因 | 根因 | 修复动作 |
|---------|------|---------|
| 内容缺失/不准确 | Coder 指令不完整 | 补充指令，重建 Coder 卡 |
| 格式损坏 | Coder 脚本 bug | 分析错误日志，修复脚本逻辑 |
| 误伤其他章节 | 定位方式不精确 | 改用更精确的定位方式（如整段 hash 匹配） |
| 安全漏洞 | Skill 缺少安全约束 | 更新 resume-ai-loop skill 的 pitfalls |
| 模型输出不稳定 | LongCat 波动 | 重试，或降级用 default profile |

**关键**：每次修复后，更新 Coder 任务的 body，加入上一轮的教训。

### 3.4 自动回滚

如果 Round 3 仍驳回，从备份快照恢复：

```bash
export $(grep -E '^FEISHU_APP_(ID|SECRET)=' /root/.hermes/.env | xargs)
# 读取最新备份
BACKUP=$(ls -t /tmp/resume_backup_*.md | head -1)
# 用 lark-cli 恢复原始内容
lark-cli docs +update --token YC6mdN1dDowEqvxqxykc33h7n3c --command overwrite --text "$(cat $BACKUP)"
```

### Coder 任务模板

```markdown
# 任务：更新飞书简历 - <章节名>（Round <N>）

## 目标
更新飞书文档「聂聃简历」中的「<章节名>」章节。

## 环境
- Feishu credentials: /root/.hermes/.env
- 文档 ID: YC6mdN1dDowEqvxqxykc33h7n3c

## 步骤
1. 读取当前文档：doc get --id YC6mdN1dDowEqvxqxykc33h7n3c
2. 定位「<章节名>」章节（精确匹配标题行）
3. 用 lark-cli docs +update --command str_replace 替换
4. 验证更新结果：重新读取文档，确认章节完整

## 新内容
<完整的新章节内容，markdown 格式>

## 上轮教训（Round 2+ 才有）
- <上一轮 Auditor 发现的问题>
- <本次修复措施>

## 安全约束
- old-text 必须包含章节标题到下一个同级标题之间的完整文本
- 不修改其他章节
- 替换后验证文档结构完整性
```

### Auditor 任务模板

```markdown
# 审计任务：简历 <章节名> 更新（Round <N>）

## 审计范围
Coder 更新了飞书文档「聂聃简历」中的「<章节名>」章节。

## 审计要点
1. 内容完整性：新章节是否包含所有关键信息，与 GitHub README 一致
2. 格式正确性：飞书文档排版正常，章节层级正确
3. 无害性：替换操作只影响目标章节，未破坏其他内容
4. 准确性：技术术语、项目名称、数据指标无误

## 审计步骤
1. 读取 Coder 交付物
2. 读取飞书文档确认内容
3. 对比 GitHub README 验证关键信息
4. 输出 6 维度格式化审计报告
```

---

## Phase 4: 通知

### 通过时

```
✅ 简历已更新

<章节名> 已更新
改动：<一句话摘要>
审计：通过

文档：https://kcnnvmk14o6i.feishu.cn/docx/YC6mdN1dDowEqvxqxykc33h7n3c
```

### 3 轮后仍驳回

```
⚠️ 简历更新失败（3 轮）

驳回原因：<Auditor 报告摘要>
已自动回滚到更新前版本
需人工介入
```

### 无变化跳过

不通知。

---

## 手动修复模式（非 cron 触发）

当用户看到 Auditor 报告后主动要求修复 P1 问题时：

1. 从飞书读取当前简历（`doc get --id <docx_id>`）
2. 按 Auditor 报告逐项修复
3. 保存为 MD 文件到 `/root/resume/`（不写飞书）
4. 文件名与飞书文档标题一致：`聂聃简历.md`、`聂聃_社会工作简历.md`
5. 用户自行审阅后决定是否同步到飞书

```bash
mkdir -p /root/resume
# 修复后保存，不调用 feishu.py doc 写入
```

> **原则**：手动修复 = 本地 MD。只有 cron 触发的自动化 Loop 才直接写飞书文档。

## Cron 配置

在知识沉淀 cron 之后运行，确保能读到当天的知识沉淀文件。

```
schedule: 40 16 * * *  (UTC) = 00:40 BJT
model: LongCat-2.0-Preview
provider: custom:Api.longcat.chat
deliver: feishu
```

知识沉淀 cron 在 00:10 BJT，留 30 分钟缓冲。

---

## 不应使用本 skill 的场景

- 简历无任何变化（GitHub 无推送、知识沉淀无新条目）→ 跳过，不通知
- 用户手动编辑了飞书文档 → 自动流程暂停，等用户确认后再跑
- 纯格式调整（改字号、调间距）→ 不需要 AI Loop
- 用户明确说"简历我自己改"→ 暂停 cron

## 常见借口与反驳（Rationalizations）

| 借口 | 现实 |
|------|------|
| "这次改动很小，不用走完整流程" | 小改动引入的错误和大改动一样多。Auditor 的 6 维度审计不因行数打折。 |
| "知识沉淀还不到 7 天，跳过 Phase 1b" | 7 天是最小窗口，不是最大。新知识沉淀可能在 7 天外仍有价值。 |
| "Coder 已经跑过测试了，Auditor 跳过" | Coder 和 Auditor 必须用不同模型，否则等于自审。这是铁律。 |
| "3 轮 Loop 太多，1 轮就够" | 3 轮是上限，不是目标。但 1 轮就过的概率很低——Auditor 的设计就是找问题。 |
| "驳回后手动修一下就行，不用重建 Coder 卡" | 手动修 = 绕过审计。AI Loop 的价值在于自动化闭环，手动干预破坏闭环。 |
| "Phase 1d 质量门太严格，错过好内容" | 质量门是"至少 2 个维度"，不是"全部 5 个"。宁可漏掉一个弱信号，不能写入噪音。 |
| "知识沉淀质量门可以靠关键词匹配" | 关键词匹配产生大量假阳性。语义判断是必须的，不能偷懒。 |

## 红旗信号（Red Flags）

- 连续 3 次运行都跳过（无变化）→ 检查 GitHub 推送是否正常、知识沉淀 cron 是否在跑
- Auditor 连续 3 次零发现 → Auditor 可能没认真审，检查审计报告内容
- Coder 卡频繁 protocol_violation → 可能是 LongCat 波动，降级用 default profile
- 飞书文档 str_replace 失败 → old-text 与文档实际文本不匹配（含换行符差异），先 `doc get` 确认
- Round 3 仍驳回且未自动回滚 → 备份快照可能丢失，立即检查 /tmp/resume_backup_*
- 简历文档被手动编辑过 → 暂停自动流程，先确认用户意图

## 互动与其他 Skill

- **`auditor`**：AI Loop 的审计闸门。Coder→Auditor 依赖链是本 skill 的核心流水线。
- **`kanban-orchestrator`**：提供 Coder/Auditor 建卡和链接的底层指令。
- **`hermes-knowledge-update`**：上游依赖——知识沉淀 cron 必须先跑（00:10 BJT），本 skill 才能读到当天数据（00:40 BJT）。
- **`feishu-lark-agent`**：飞书文档读写。str_replace 精确匹配是最大踩坑点。
- **`doubt-driven-development`（agent-skills 参考）**：Coder 执行过程中可插入 DDD 检查点，在代码提交前就质疑，降低 Auditor 驳回率。

## 验证清单（Verification）

每次运行完成后逐项确认：

- [ ] Phase 1a：GitHub 项目列表已拉取（`gh repo list`）
- [ ] Phase 1b：飞书简历已实际读取（`doc get`）
- [ ] Phase 1c：知识沉淀文件已读取（最近 7 天）
- [ ] Phase 1d：质量门已过滤，只保留 ≥2 维度的条目
- [ ] Phase 2：差距分析已完成，改动决策有明确理由
- [ ] Phase 3：备份快照已创建（`/tmp/resume_backup_*.md`）
- [ ] Phase 3：Coder 和 Auditor 使用了不同模型
- [ ] Phase 3：Loop 轮数 ≤ 3，第 3 轮仍驳回已自动回滚
- [ ] Phase 4：通过时已发送飞书通知；无变化时静默跳过
- [ ] 飞书文档未被手动编辑过（检查 `doc get` 的修改时间）

## 活跃踩坑

- **Coder 和 Auditor 必须用不同模型**：Coder=LongCat，Auditor=DeepSeek 官方，否则等于自审
- **Coder 无飞书发送能力**：通知由 Planner 发送，不在 Coder/Auditor 的 prompt 里写「发飞书」
- **飞书文档 str_replace 精确匹配**：old-text 必须与文档中实际文本完全一致（包括换行符），否则替换失败
- **知识沉淀质量门不能靠关键词**：需要语义判断，不能简单正则匹配
- **Loop 上限 3 轮**：防止无限循环烧 Token
- **LongCat 在 kanban worker 模式下可能 protocol_violation**（2026-06-22 世界杯预测实战）：Coder 卡（reasonix/LongCat）跑完代码后不调 `kanban_complete`，直接退出。表现：worker exited cleanly (rc=0) without calling kanban_complete。**解法**：确定性脚本由 Planner 直接跑，不建 Coder 卡。只有需要 LLM 生成代码的任务才用 Coder 卡，且需在 prompt 里硬写「完成后必须调 kanban_complete」。
- **量化指标必须逐项核对源材料**（2026-06-22）：简历中的每个数字都必须在 GitHub README/docs 中找到对应出处。格式合规性 ≠ 解读一致性，不可混用指标。无源码支撑的 benchmark 一律删除或标注「自测」
- **DSPy 指标混淆陷阱**：`DSPY_INTEGRATION.md` 中的 95% 是**格式合规性**（format compliance），不是**解读一致性**（interpretation consistency，实际 90%）。简历中写"解读一致性达95%"属于误标——Auditor 会抓到。正确写法：`DSPy格式合规性达95%，解读一致性达90%`
- **量化成果必须有源码支撑**：如"处理时间从30分钟缩短至3分钟"这类 benchmark，若 README/docs 中无对应数据，Coder 不应编造。要么标注"（自测）"，要么删除

## 关联

- `kanban-orchestrator`：AI Loop 流水线模式
- `auditor`：代码审计 6 维度标准
- `feishu-lark-agent`：飞书文档读写
- `hermes-knowledge-update`：知识沉淀 cron（本 skill 的上游依赖）
- `references/lab-analysis-resume-template.md`：Lab-Analysis 简历改写实战案例