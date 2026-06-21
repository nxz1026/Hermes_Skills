# LongCat-2.0-Preview 使用反馈（提交给官方）

**提交对象**：LongCat 官方团队  
**提交时间**：2026-06-21  
**使用场景**：Hermes Agent 生产环境编码/文档生成任务  
**测试模型**：LongCat-2.0-Preview（内测阶段）

---

## Bug 报告

### 1. `thinking` 参数布尔值 `false` 无效

**现象**：API 请求中设置 `"thinking": false` 无法关闭 thinking 模式，模型仍然输出 thinking 内容。

**期望行为**：`thinking: false` 应等价于关闭 thinking。

**实际行为**：只有 `"thinking": {"type": "disabled"}` 嵌套对象格式才能关闭。

**影响**：文档未说明此差异，用户容易误用布尔值格式导致 unexpected token 消耗。

**建议**：
- 支持布尔值 `false` 作为关闭 thinking 的快捷方式
- 或在 API 文档中明确说明仅支持对象格式

---

### 2. 长上下文检索质量

**现象**：在 50-200 轮真实对话场景中，长上下文指令跟随和远端信息召回准确率偏低。

**测试数据**：基于真实 agent.log 的 benchmark（8 项测试，LongCat 得分 75%，对比 MiniMax-M3 47%），长上下文检索和复杂规划场景失分较多。

**建议**：优化长上下文下的 attention 检索精度，或在 API 层面提供可选的 retrieval-augmented 模式。

---

## 改进建议

| # | 建议 | 优先级 |
|---|------|--------|
| 1 | `thinking` 参数支持布尔值 `false` | P1 |
| 2 | 明确 API 文档中 `thinking` 参数支持的类型格式 | P1 |
| 3 | 优化长上下文（>100K tokens）下的指令跟随质量 | P2 |

---

*测试环境：Linux 6.8.0, Hermes Agent 2026-06-21, reasonix v0.53.2*
