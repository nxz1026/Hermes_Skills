---
name: evolve-skill
description: Skill 进化 — 用 skill-evolution CLI 或 raw API 优化 SKILL.md。默认 LongCat-2.0-Preview（OpenAI 协议）。自动保留 frontmatter + 审计解读。
version: 1
---

# Evolve Skill — Skill 进化工作流

**触发**：用户说"给 X skill 跑进化"、"优化 SKILL.md"、"瘦身"、"evolution"。

## Provider 选择（优先级）

| 优先级 | Provider | 协议 | 模型 | 场景 |
|--------|----------|------|------|------|
| P0 | LongCat | OpenAI | LongCat-2.0-Preview | **默认** |
| P1 | DeepSeek 官方 | OpenAI | deepseek-chat | 用户明确指定后 |

**铁律**：默认 LongCat。只有用户明确说"用 DeepSeek"才切。

## 步骤

### Step 1: 准备进化工作区

```bash
WORKDIR="/tmp/evolve-<skill-name>"
mkdir -p $WORKDIR
cp /path/to/SKILL.md $WORKDIR/SKILL.md
```

创建 `$WORKDIR/tasks.txt` — 每行一个任务描述，覆盖：
- 常规案例（2-3 个）
- 边界情况（1-2 个）
- 具体到该 skill 的典型场景

### Step 2: 预检 key

跑进化前先测 key 有效性，避免白等 30 分钟。

```bash
# LongCat key 连通性测试
python3 -c "
import os, requests
env_file = os.path.expanduser('~/.hermes/.env')
with open(env_file) as f:
    for line in f:
        if 'LONGCAT_API_KEY' in line and '=' in line:
            key = line.split('=', 1)[1].strip()
            break
r = requests.post('https://api.longcat.chat/openai/v1/chat/completions',
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={'model': 'LongCat-2.0-Preview', 'messages': [{'role': 'user', 'content': 'OK'}], 'max_tokens': 10})
print(f'OK — status={r.status_code}, model={r.json().get(\"model\", \"?\")}')
"
```

### Step 3: 跑进化

#### 方式 A：skill-evolution CLI（推荐，含审计）

```bash
cd $WORKDIR

# LongCat（OpenAI 协议）
export OPENAI_API_KEY=$(grep '^LONGCAT_API_KEY=' ~/.hermes/.env | cut -d= -f2-)
python3 -m skill_evolution.cli evolve \
  -p openai -m LongCat-2.0-Preview \
  --base-url https://api.longcat.chat/openai/v1 \
  -r 2 -k 3 \
  -o skill.evolved.md SKILL.md tasks.txt
```

#### 方式 B：raw API 脚本（单 skill 快速进化）

`evolve_wcp.py` 模式 — 简单 urllib 直接进化。

```python
# /tmp/evolve_raw.py
import os, json, time, re, urllib.request
from pathlib import Path

SKILL_PATH = Path("/path/to/SKILL.md")
BACKUP_PATH = SKILL_PATH.with_suffix(".md.bak-evolution")

# 读 key（改用脚本中 evolve_raw.py 或直接调 skill 自带脚本）
# python3 /root/.hermes/skills/devops/evolve-skill/scripts/evolve_raw.py /path/to/SKILL.md
```

**raw API 进化 prompt 要点（hard constraints 防止砍关键）**：

```
你是 Hermes SKILL.md 优化专家。精简+重组,但保留所有关键功能。

硬约束:
1. frontmatter 保留: name, description
2. version 必须是 integer (如 2)
3. 保留每个 Step 的完整细节（含命令块、表格、代码示例、bash/python/yml代码块）
4. 保留所有"踩坑"条目（列表格式不变，逐条保留，不合并不删减）
5. 保留关键执行步骤/流程顺序
6. 保留Provider配置表和优先级表（如有）
7. 保留报告格式模板（如有）
8. 保留核心数据字典（如有）
9. 不删 P2 算法公式 (如有)

可优化: 删冗余/合并/简化/重组

输出: 完整 SKILL.md (frontmatter + markdown body),无前后缀说明。
```

**自进化警示**：raw API 的硬约束对"流程型（Step 步骤 + CLI 命令 + 踩坑列表）"skill 仍然不可靠。2026-06-18 用本 skill 进化自身，6KB→569 bytes（-91%），所有 Step 细节、踩坑 12 条、审计表全部丢失。`保留关键执行步骤` 和 `保留踩坑小节` 两个约束没能阻止模型砍内容。**无论用哪种方式，跑完后必须检查保留的内容是否完整。**

### Step 4: 保留 frontmatter

`skill-evolution` 输出会覆盖 frontmatter（name→untitled, description 丢失）。

```bash
python3 /root/.hermes/skills/devops/evolve-skill/scripts/apply_evolution.py \
  /path/to/original/SKILL.md \
  $WORKDIR/skill.evolved.md
```

### Step 5: 审计解读

| audit 结果 | 常见原因 | 是否采纳 |
|------------|---------|---------|
| PASS | 进化成功 | ✅ 采纳 |
| warning（硬编码路径/cron ID/username）| 私用 skill 的正常现象 | ✅ 采纳 |
| FAIL（硬编码私用信息）| 同上 | ✅ 采纳 |
| FAIL（自相矛盾/业务规则错误）| 进化引入矛盾 | ❌ 退回 Round 1 snapshot |
| FAIL（砍到空壳/失核心）| 过度优化 | ❌ 退回原始版 |

### Step 6: 验证

```bash
# 1. 大小变化
wc -c $WORKDIR/SKILL.md $WORKDIR/skill.evolved.md

# 2. frontmatter 完整性
head -8 /path/to/SKILL.md

# 3. 关键内容保留
grep -c "关键命令\|关键章节名" /path/to/SKILL.md
```

### Step 7: 替换

```bash
cp /path/to/SKILL.md /path/to/SKILL.md.bak.$(date +%Y%m%d)
cp $WORKDIR/skill.evolved.md /path/to/SKILL.md
```

## 报告格式

```
### {skill_name} 进化结果

| 项 | 原版 | 新版 | 变化 |
|----|------|------|------|
| 大小 | {N} bytes | {M} bytes | **{delta}%** |
| frontmatter | ✅/❌ | ✅/❌ | {status} |
| 关键命令 | ✅/❌ | ✅/❌ | {status} |
| {核心内容} | ✅/❌ | ✅/❌ | {status} |

### 保留的
- ...

### 砍掉的
- ...

### audit
{audit output summary}

### 结论
{采纳/回退/重跑}
```

## 踩坑

1. **不先测 key** — 等了 30 分钟发现全程 401。**跑前必测**。
2. **LongCat-2.0-Preview 走 OpenAI 协议** — base_url 是 `https://api.longcat.chat/openai/v1`，用 `-p openai`。不要用 `-p claude`。
3. **openmodel.ai 走 Anthropic 协议** — 不是 OpenAI 协议。`/v1/chat/completions` 永远 404。用 `ANTHROPIC_BASE_URL=https://api.openmodel.ai`（不加 `/v1`）。
4. **base_url 必须带 /v1（DeepSeek 官方）** — `api.deepseek.com` → 401/404。`api.deepseek.com/v1` → OK。
5. **Key 末尾 \n** — shell 截断或残留，用 Python `strip()` + `rstrip()`。
6. **SKILL.md version 必须 integer** — `version: 2.0.0` → Pydantic validator 报错 → name=untitled。用 `version: 2`。
7. **shell heredoc 含 `KEY=VALUE` 被脱敏** — 用 `write_file` 工具代替 `terminal heredoc`。
8. **绝对路径 + cwd 默认** — 输出落 CWD 不到目标目录。必须 `basename + cwd=` 传参。
9. **"changes applied" 为空但 audit 仍跑** — 检查 `evolution_round` 字段，为 0 说明未应用。
10. **保护任务无效** — reference 型 skill（Provider 表/Troubleshooting）不保留参考内容，进化会砍掉所有参考表。
11. **后台跑必须 notify_on_complete=true** — 否则跑完无法自动收到通知。
12. **raw API 方式更可控** — `skill_evolution.cli` 会按自己逻辑砍内容；raw API 加 hard constraints 能更好保留关键内容。
13. **CLI 超时风险** — `-r 2 -k 3` 跑小 skill（6KB）也可能在 Round 2 超时（300s 不够）。**< 10KB 的 skill 优先用 raw API**，CLI 留给 > 15KB 的 skill。
14. **自进化悖论：约束不够具体** — 2026-06-18 实测 raw API 进化自身，6KB→569 bytes（-91%），`保留关键执行步骤` + `保留踩坑小节` 两个约束被模型无视。**教训**：hard constraints 必须逐条列举具体内容类型（"保留每个 Step 的完整细节含命令块""保留全部踩坑逐条""保留Provider配置表"），泛泛表述无效。跑完后**必须人工对比保留/砍掉清单**。
