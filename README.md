这份说明文档将为你详细拆解这款 **"PM-Agent APP"** 的内核。为了实现从一个模糊想法到全套 PRD 的产出，我们需要构建一个**"虚拟产研中心"**。

---

## 一、 智能体角色定义 (Agent Roles)

我们采用**"执行者-评论家" (Actor-Critic)** 架构模式，包含 7 个核心智能体：

| 智能体名称 | 核心职责 | 关键技能 (Tools/Skills) |
| --- | --- | --- |
| **0. 首席产品官 (Senior PM Agent)** | **质量闸门系统**：负责需求准入验证与各阶段产出审计，通过统一 JSON 契约输出评分（0-10分）与修改指令。 | 商业价值评估、逻辑深度审计、量化打分、流程拦截。 |
| **1. 需求分析专家 (Discovery Agent)** | 引导用户细化想法，将一句"我想做..."变成结构化的《产品定义锚点》。 | 提问引导、用户画像建模、痛点识别、业务实体提取。 |
| **2. 深度访谈式调研专家 (Researcher Agent)** | 充当"专业信息挖掘者"，通过向用户提问引导其提供行业内幕、竞品情报或业务文档。 | 访谈式调研策略、对标分析、避坑指南、差异化建议。 |
| **3. 逻辑架构师 (Architect Agent)** | 将业务需求转化为底层逻辑。输出业务流程和功能清单。 | Mermaid 代码生成（画图）、信息架构设计。 |
| **4. 逻辑审计员 (Reviewer Agent)** | 扮演"杠精"开发，专门寻找逻辑漏洞和缺失的异常分支。 | 逻辑校验、边界情况 (Edge Cases) 模拟。 |
| **5. 文档专家 (Writer Agent)** | 整合所有信息，按照标准 PRD 模板输出文档。 | Markdown 格式化、专业术语转换、文档导出。 |
| **6. 文档归档员 (Document Auditor)** | 自动化归档各阶段产出物，确保知识沉淀。 | 文件管理、版本控制、结构化存储。 |

---

## 二、 架构模式：统一契约 + 后端编排 (Unified Contract + Backend Orchestration)

我们采用**"统一契约 + 后端过滤"**的高级架构模式，确保用户体验的流畅性与系统逻辑的严谨性。

### 核心设计原则

1. **统一契约 (Unified Contract)**：Senior PM Agent 始终输出标准化的 JSON 格式，包含 `verdict`、`score`、`human_message`、`system_instructions` 等字段。
2. **后端过滤 (Backend Filtering)**：编排层（自定义 `BaseAgent`）拦截 PM 的原始 JSON，提取 `human_message` 给用户，提取 `system_instructions` 给执行者，实现"人机交互"与"机机协作"的分离。
3. **状态持久化 (State Persistence)**：使用 `ctx.actions.state_delta` 进行状态更新，确保所有关键决策（如准入通过、审计结果）被正确持久化。

### 阶段 1：需求对齐 (Discovery Phase)

* **架构模式**：自定义 `BaseAgent`（`DiscoveryPhaseAgent`）管理全流程
* **子阶段流程**：
  1. **准入验证 (Sanity Check)**：Senior PM 审计用户输入，输出 JSON。代码提取 `human_message` 温和引导用户。
  2. **需求挖掘 (Mining Loop)**：Discovery Expert 与用户进行多轮启发式对话，直到产出《产品定义锚点》。
  3. **质量审计 (Final Audit)**：Senior PM 审计终产物，评分 >= 6 分则通过并触发文档归档。
* **产出**：《产品定义锚点 (Discovery Anchor)》，包含：核心价值主张、业务实体、黄金路径用户故事、项目边界。

### 阶段 2：逻辑与可行性建模 (Logic & Feasibility Phase)

* **架构模式**：层级协作（Hierarchical）
* **参与者**：Researcher → Architect → Reviewer → Architect
* **质量拦截**：每个子阶段完成后，Senior PM 进行审计，不合格（< 6分）则打回修正。
* **产出**：《业务逻辑蓝图》，包含：Mermaid 流程图、功能矩阵、异常处理清单。

### 阶段 3：文档标准化 (Documentation Phase)

* **参与者**：Writer Agent
* **任务**：将确认的"蓝图"翻译成标准 PRD。
* **产出**：最终交付物 `Product_Requirement_Document.md`。

---

## 三、 工作流详细数据流转 (Data Flow)

### 3.1 状态管理机制

**关键原则**：所有状态修改必须通过 `ctx.actions.state_delta`，确保持久化与审计追踪。

```python
# ✅ 正确做法
ctx.actions.state_delta["is_sanity_passed"] = True
ctx.actions.state_delta[pm_output_key] = pm_report

# ❌ 错误做法（不会持久化）
ctx.session.state["is_sanity_passed"] = True
```

### 3.2 数据流转路径

1. **State Init:** 通过 `state_delta` 初始化 `discovery_output` 占位符。
2. **准入验证:** Senior PM 输出 JSON → 代码解析 → `state_delta` 更新 `is_sanity_passed` → 用户看到 `human_message`。
3. **需求挖掘:** Discovery Expert 输出 → `state_delta` 更新 `discovery_output` → 检测到"需求挖掘已完成"标志位。
4. **质量审计:** Senior PM 输出 JSON → 代码解析 → `state_delta` 更新审计报告 → 分数 >= 6 触发 `ctx.actions.escalate = True`。
5. **文档归档:** Document Auditor 读取 `doc_archive_request` → 归档终产物。
6. **逻辑建模:** Researcher/Architect/Reviewer 协作，每个子阶段由 Senior PM 审计。
7. **最终交付:** Writer Agent 读取所有 state，生成 PRD。

---

## 四、 关键交付物结构 (Deliverables)

### 4.1 阶段一产出：产品定义锚点 (Discovery Anchor)

由 Discovery Expert 产出，包含：
- **核心价值主张 (CVP)**：一句话描述产品如何解决核心痛点。
- **业务实体 (Entities)**：为 Architect 提供建模基础的关键名词。
- **黄金路径用户故事**：3-5 个核心用户故事（格式：作为[角色]，我想要[动作]，以便[价值]）。
- **项目边界**：明确"本版本不做"的功能（Scope Out）。

### 4.2 阶段二产出：业务逻辑蓝图

由 Architect + Researcher + Reviewer 协作产出，包含：
- **业务流程图**：使用 Mermaid 渲染的逻辑图（必须包含异常分支）。
- **功能矩阵**：每个功能点的输入、处理、输出逻辑。
- **竞品对标分析**：由 Researcher 提供的差异化建议。
- **异常处理清单**：由 Reviewer Agent 贡献的各类错误处理逻辑。

### 4.3 阶段三产出：最终 PRD 文档

由 Writer Agent 产出，包含：
- **文档信息**：修订记录、项目背景。
- **业务流程图**：使用 Mermaid 渲染的逻辑图。
- **核心功能说明**：每一个功能点的输入、处理、输出逻辑。
- **非功能性需求**：性能要求、安全性、埋点需求。
- **异常处理清单**：由 Reviewer Agent 专门贡献的各类错误处理逻辑。

---

## 五、 核心技术架构 (Technical Architecture)

### 5.1 统一契约模式 (Unified Contract Pattern)

**Senior PM Agent** 作为质量裁判，始终输出标准 JSON：
```json
{
  "verdict": "PASS" | "REJECT",
  "score": float (0.0-10.0),
  "human_message": "给用户的温和引导语",
  "system_instructions": "给执行者的处方级指令",
  "audit_metadata": {...}
}
```

### 5.2 后端过滤机制 (Backend Filtering)

编排层（自定义 `BaseAgent`）负责：
- **拦截 JSON**：静默运行 PM，捕获其输出。
- **消息过滤**：提取 `human_message` 给用户，提取 `system_instructions` 给执行者。
- **流程控制**：根据 `verdict` 和 `score` 决定是否 `escalate`。

### 5.3 状态持久化最佳实践

**必须使用 `ctx.actions.state_delta`**：
- 确保状态变更被事件系统追踪。
- 保证跨会话的持久化。
- 支持审计日志记录。

### 5.4 执行者-评论家模式 (Actor-Critic Pattern)

- **执行者 (Actor)**：Discovery、Architect、Researcher 等，负责产出内容。
- **评论家 (Critic)**：Senior PM，负责量化评分与拦截。
- **迭代机制**：如果评分 < 6 分，执行者根据 `system_instructions` 修正后重新提交。

---

## 六、 使用指南 (Usage Guide)

### 6.1 启动应用

```bash
# 启动 ADK Web 服务器
adk web --reload --reload_agents
```

访问 `http://localhost:8000` 进行交互。

### 6.2 工作流示例

1. **用户输入**："我想做一个相机出租小程序"
2. **Senior PM 准入**：审计通过，输出 `human_message`："需求合法，已转交给需求专家为您服务。"
3. **Discovery Expert**：与用户多轮对话，挖掘痛点、实体、边界。
4. **Discovery Expert 产出**：输出《产品定义锚点》，包含 `[Discovery_Expert] 需求挖掘已完成` 标志位。
5. **Senior PM 审计**：评分 >= 6，触发文档归档并 `escalate` 到下一阶段。
6. **后续阶段**：逻辑建模 → 文档标准化。

### 6.3 调试技巧

- **查看 Session State**：在代码中使用 `logger.debug(f"State: {ctx.session.state}")`。
- **检查状态持久化**：确认所有状态修改都使用了 `ctx.actions.state_delta`。
- **JSON 解析问题**：如果遇到 `Extra data` 错误，检查 `_parse_json` 函数是否正确处理了并排 JSON。
