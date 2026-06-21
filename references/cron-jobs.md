# Cron 任务清单

> 数据来源：`cronjob list` (Hermes cron 调度器)
> 提取时间：2026-06-21
> 共 8 个任务，全部 enabled，全部 deliver 到 feishu

---

## 1. 📰 每日晨报

| 字段 | 值 |
|------|------|
| **name** | 📰 每日晨报 |
| **job_id** | `a86e763867c4` |
| **schedule** | `10 23 * * *` (每天 23:10 UTC = 07:10 BJT) |
| **provider** | `custom:Api.longcat.chat` |
| **model** | `LongCat-2.0-Preview` |
| **skills** | `hermes-daily-morning-report` |
| **enabled_toolsets** | `web`, `terminal`, `file` |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | 调用 hermes-daily-morning-report skill，按模块顺序生成晨报（中东模块已取消，共 8 个模块） |

---

## 2. 日志扫描

| 字段 | 值 |
|------|------|
| **name** | 日志扫描 |
| **job_id** | `014b2b65edd5` |
| **schedule** | `20 17 * * *` (每天 17:20 UTC = 01:20 BJT) |
| **provider** | `custom:Api.longcat.chat` |
| **model** | `LongCat-2.0-Preview` |
| **skills** | `log-daily-scan` |
| **enabled_toolsets** | `terminal`, `file` |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | Hermes 日志扫描 agent，每天 01:20 BJT 启动，所有修复动作由 agent 独立判断并执行 |

---

## 3. 🛌 SkillOpt-Sleep weekly

| 字段 | 值 |
|------|------|
| **name** | 🛌 SkillOpt-Sleep weekly |
| **job_id** | `757b1c39b62c` |
| **schedule** | `10 21 * * 0` (每周日 21:10 UTC = 05:10 BJT 周一) |
| **provider** | `custom:Api.longcat.chat` |
| **model** | `LongCat-2.0-Preview` |
| **skills** | `skillopt-integration` |
| **enabled_toolsets** | `terminal`, `file` |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | 加载 skillopt-integration skill，按 SKILL.md 运行每周 SkillOpt-Sleep sleep cycle，输出摘要到飞书 |

---

## 4. ⚽ 世界杯预测(一体化)

| 字段 | 值 |
|------|------|
| **name** | ⚽ 世界杯预测(一体化) |
| **job_id** | `84d210ffeedc` |
| **schedule** | `30 2 * * *` (每天 02:30 UTC = 10:30 BJT) |
| **provider** | `custom:Api.longcat.chat` |
| **model** | `LongCat-2.0-Preview` |
| **skills** | `world-cup-predict` |
| **enabled_toolsets** | `web`, `terminal`, `file` |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | 加载 world-cup-predict skill，先回抓真实结果写入 results，再跑预测 pipeline |

---

## 5. 🎯 接活雷达 + 成都招聘（晚间版）

| 字段 | 值 |
|------|------|
| **name** | 🎯 接活雷达 + 成都招聘（晚间版） |
| **job_id** | `d577c98a2334` |
| **schedule** | `30 10 * * *` (每天 10:30 UTC = 18:30 BJT) |
| **provider** | `custom:Api.longcat.chat` |
| **model** | `LongCat-2.0-Preview` |
| **skills** | `freelance-radar` |
| **enabled_toolsets** | (未限制) |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | 加载 freelance-radar skill，分两步执行（接活 + 招聘），合并为一条报告投递飞书 |

---

## 6. 📚 IMA知识库更新

| 字段 | 值 |
|------|------|
| **name** | 📚 IMA知识库更新 |
| **job_id** | `0e1d8854f689` |
| **schedule** | `10 16 * * *` (每天 16:10 UTC = 00:10 BJT) |
| **provider** | `custom` |
| **model** | (null — 使用 provider 默认) |
| **skills** | (无) — prompt 直接引用 `hermes-knowledge-update` skill |
| **enabled_toolsets** | `web`, `terminal`, `file` |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | 加载 hermes-knowledge-update skill，执行知识沉淀（蒸馏当天飞书/微信对话 → 免费资源更新） |

---

## 7. 📊 模型健康报告

| 字段 | 值 |
|------|------|
| **name** | 📊 模型健康报告 |
| **job_id** | `2e3752f1128d` |
| **schedule** | `0 18 * * *` (每天 18:00 UTC = 02:00 BJT) |
| **provider** | (null) |
| **model** | (null) |
| **skills** | (无) — 直接运行脚本 |
| **enabled_toolsets** | `terminal` |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | 运行 `~/.hermes/scripts/model_health.py`，分析近 24h 数据（滚动窗口），输出紧凑格式到飞书 |

---

## 8. 📊 模型标杆测试

| 字段 | 值 |
|------|------|
| **name** | 📊 模型标杆测试 |
| **job_id** | `4cc5d1249962` |
| **schedule** | `0 22 * * *` (每天 22:00 UTC = 06:00 BJT) |
| **provider** | `custom` |
| **model** | (null — 脚本内部配置) |
| **skills** | (无) — 直接运行脚本 |
| **enabled_toolsets** | `terminal` |
| **deliver** | `feishu` |
| **last_status** | `ok` |
| **prompt摘要** | 运行 `~/.hermes/scripts/model_benchmark.py`，对 LongCat 和 MiniMax-M3 跑 7 个固定用例对比测试，输出紧凑格式到飞书 |

---

## 汇总

| 时间 (UTC) | 时间 (BJT) | 任务 | 类型 |
|------------|-----------|------|------|
| 02:30 | 10:30 | ⚽ 世界杯预测 | 定时 + skill |
| 10:30 | 18:30 | 🎯 接活雷达 | 定时 + skill |
| 16:10 | 00:10 | 📚 IMA知识库 | 定时 + prompt |
| 17:20 | 01:20 | 日志扫描 | 定时 + skill |
| 18:00 | 02:00 | 📊 模型健康 | 定时 + 脚本 |
| 22:00 | 06:00 | 📊 模型标杆 | 定时 + 脚本 |
| 23:10 | 07:10 | 📰 每日晨报 | 定时 + skill |
| Sun 21:10 | Mon 05:10 | 🛌 SkillOpt | 每周 + skill |
