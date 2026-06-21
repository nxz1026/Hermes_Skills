# 自建脚本清单

> 数据来源：`~/.hermes/scripts/` 目录扫描
> 提取时间：2026-06-21
> 共 19 个脚本文件（含 1 个 .pyc 缓存）

---

## 核心脚本

### 1. `model_benchmark.py`
- **用途**：模型标杆测试 v2 — 基于真实对话历史（state.db 提取的夹具），对比 LongCat vs MiniMax-M3
- **用法**：`python3 model_benchmark.py [--models LongCat DeepSeek] [--compact] [--extract] [--output]`
- **依赖**：`extract_benchmark_fixtures.py`
- **输出**：控制台 + 可选写入 `~/.hermes/data/benchmark_history.json`

### 2. `extract_benchmark_fixtures.py`
- **用途**：从 `state.db` 提取真实会话作为 benchmark 测试夹具
- **用法**：`python3 extract_benchmark_fixtures.py`
- **输出**：`~/.hermes/data/benchmark_fixtures/` 下的 JSON 文件

### 3. `model_health.py`
- **用途**：模型健康报告 v2 — 分析 `agent.log` 按模型汇总延迟/错误/用量
- **用法**：`python3 model_health.py [--hours 72] [--days 7] [--compact] [--output]`
- **输出**：文本报告，写入 `~/.hermes/cron/output/`

### 4. `Log_daily_status.py`
- **用途**：每日 LLM/系统 日报（北京时间 24h 滚动窗口）
- **数据源**：`~/.hermes/logs/{agent,gateway,errors}.log` + `/var/log/{syslog,auth.log,kern.log}`
- **用法**：`python3 Log_daily_status.py [--persist] [--fix]`
- **输出**：文本报告（喂给 cron 投递飞书）

### 5. `token_stats.py`
- **用途**：每日 Token 统计 v5（按 LLM × Provider 分组）
- **用法**：`python3 token_stats.py [--24h] [--compact]`
- **特性**：合并读取 `agent.log` + `bounty_tokens.csv`，北京时间凌晨 1:00 自动清零

### 6. `predict_wc.py`
- **用途**：World Cup Predict v2 — 结构化预测引擎
- **用法**：`python3 predict_wc.py [--dates YYYYMMDD-YYYYMMDD] [--no-fetch]`
- **输出**：JSON 写入 `/root/football/predictions/`，校准写入 `/tmp/pred_calibration.json`

### 7. `ima_kb.py`
- **用途**：IMA 知识库管理脚本（笔记本/笔记/文件夹的 CRUD 操作）
- **用法**：`python3 ima_kb.py {list_notebooks,search_notes,get_note,create_note,list_folders,create_folder,seed_ai_kb,seed_free_resources}`
- **依赖**：`ima-skill` skill 目录中的 `ima_api.cjs`

### 8. `ima_seed_free.py`
- **用途**：灌入免费 AI Token 资源到 IMA 知识库 "白嫖资源" 文件夹
- **用法**：`python3 ima_seed_free.py`
- **目标**：KB_ID=`RiAyZ6HYD-RRnH1UrNp0gOrHjq5d5nkYoudomp4p6Ek=`

### 9. `genimg.py`
- **用途**：免费图生包装，支持多个后端（Pollinations.ai、Dashscope 通义万相等）
- **用法**：`python3 genimg.py`
- **特性**：从 `.env` 读取 API key

### 10. `dl_tongyi.py`
- **用途**：下载通义万相图片结果（一次性脚本）
- **用法**：`python3 dl_tongyi.py`
- **输出**：`/tmp/tongyi_kratos_wukong.jpg`

### 11. `longcat_thinking_test.py`
- **用途**：LongCat thinking 污染复现测试
- **用法**：`python3 longcat_thinking_test.py`
- **输出**：`/root/.hermes/data/longcat_thinking_test/`

### 12. `longcat_thinking_test.sh`
- **用途**：LongCat thinking 污染复现测试（Shell 版，2026-06-20）
- **用法**：`bash longcat_thinking_test.sh`
- **输出**：`/root/.hermes/data/longcat_thinking_test/full_log.txt`

---

## 运维脚本

### 13. `backup.sh`
- **用途**：每日备份（每天 08:55 跑，在晨报前完成）
- **备份内容**：`.env | config.yaml | secrets.yaml | memory | skills | cron | scripts | Lab-Analysis`
- **保留策略**：7 天自动清理
- **输出**：`~/.hermes/backups/*.tar.gz` + `~/.hermes/cron/output/backup_status.txt`

### 14. `openhands-run`
- **用途**：一键派活给 OpenHands（走 OpenRouter）
- **用法**：`openhands-run -t '任务描述' [--resume <uuid>]`
- **默认模型**：`openrouter/openai/gpt-4o-mini`

### 15. `log_daily_status_cron.sh`
- **用途**：`Log_daily_status.py` 的 cron 包装器
- **用法**：`bash log_daily_status_cron.sh`（等价于 `python3 Log_daily_status.py --persist --fix`）

### 16. `check_secret_integrity.sh`
- **用途**：密钥完整性校验（输出 sha256，不打印明文）
- **用法**：`check_secret_integrity.sh <ENV_VAR_NAME> [SHA256_HASH]` 或 `--all`

### 17. `bw_unlock.sh`
- **用途**：Bitwarden 解锁助手
- **用法**：`bw_unlock.sh`（从 `.env` 读 `BW_PASSWORD`）

### 18. `jina-fetch.sh`
- **用途**：Jina Reader API 包装器
- **用法**：`jina-fetch.sh <url> | --search "<query>" | --raw <url> | --html <url>`

### 19. `hindsight-upgrade.sh`
- **用途**：升级 Hindsight Docker 部署（持久化模式）
- **用法**：`hindsight-upgrade.sh [--dry-run] [--rollback]`
- **已知坑**：
  - 仓库只发布 `:latest` 和 `:latest-slim`，无版本号 tag
  - 默认 worker ID = 容器 hostname → Docker 重启会变 → zombie operations
  - `retain_async=true` 会让 LLM 失败时 silent drop

---

## 目录结构

```
~/.hermes/scripts/
├── model_benchmark.py              # 模型对比测试
├── extract_benchmark_fixtures.py   # 从 state.db 提取测试夹具
├── model_health.py                 # 模型健康报告
├── Log_daily_status.py             # 每日系统日报
├── token_stats.py                  # Token 用量统计
├── predict_wc.py                   # 世界杯预测
├── ima_kb.py                       # IMA 知识库管理
├── ima_seed_free.py                # IMA 免费资源灌入
├── genimg.py                       # 免费图生
├── dl_tongyi.py                    # 通义图片下载
├── longcat_thinking_test.py        # LongCat thinking 测试
├── longcat_thinking_test.sh        # LongCat thinking 测试(Shell)
├── openhands-run                   # OpenHands 一键派活
├── backup.sh                       # 每日备份
├── log_daily_status_cron.sh        # 日报 cron 包装
├── check_secret_integrity.sh       # 密钥完整性校验
├── bw_unlock.sh                    # Bitwarden 解锁
├── jina-fetch.sh                   # Jina Reader 包装
├── hindsight-upgrade.sh            # Hindsight 升级
└── __pycache__/                    # Python 缓存
    └── predict_wc.cpython-311.pyc
```
