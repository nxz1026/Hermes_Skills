# Hermes 工具链踩坑记录（内部参考）

> 以下问题与 LongCat 模型本身无关，是 Hermes/工具链层面的踩坑，供内部优化参考。

---

## T4: write_file 工具写入 JSON 时的 UTF-8 列偏移 bug

**现象**：写入包含 emoji key 的 JSON 文件后，lint 报 `JSONDecodeError`。实际文件检查发现 `provider` 字段起始双引号缺失。

**根因**：write_file 的 JSON linter 对 UTF-8 多字节字符的 offset 计算有误。

**Workaround**：写入后用 `python3 -c "import json; json.load(open(...))"` 验证，手动修复。

**影响**：导致 cron-jobs.json 结构损坏，需 Python 脚本逐行修复。

---

## T6: setup.sh `--dry-run` 参数设计

**现象**：用户尝试 `./setup.sh --dry-run` 报错 "Unknown arg"。

**根因**：脚本默认即为 dry-run 模式，未将 `--dry-run` 设为 no-op。

**改进**：参数解析中增加 `--dry-run)` no-op 分支。

---

## T6: shellcheck 6 个 SC2034 警告

**涉及变量**：`VERBOSE`, `toolset_flag`, `model_flag`, `prompt_override`, `has_ssh_rate`

**根因**：预留变量或未完成功能占位，未加注释。

**改进**：删除或加 `# reserved for future use` 注释。

---

## T6: provider 路由 fallback 行为

**现象**：`provider: custom`（未指名具体 provider）时，系统 fallback 到全局默认 provider（OpenModel），而非 LongCat。

**根因**：Hermes 路由逻辑中 `custom` 与 `custom:<name>` 的匹配机制不透明。

**改进**：文档明确 fallback 行为；未匹配时输出 warning 日志。

---

## T6: `api_mode` 全局/局部继承机制

**现象**：全局 `api_mode: anthropic_messages` 未被 per-provider 覆盖时，LongCat 收到错误格式请求返回 404。

**根因**：`api_mode` 的继承规则未在文档中说明。

**改进**：文档明确全局默认 vs per-provider 覆盖的优先级。
