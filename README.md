这份说明文档将为你详细拆解这款 **“PM-Agent APP”** 的内核。为了实现从一个模糊想法到全套 PRD 的产出，我们需要构建一个**“虚拟产研中心”**。

---

## 一、 智能体角色定义 (Agent Roles)

我们需要 5 个核心智能体，每个 Agent 都有其独特的 `System Instruction` 和工具权限。

| 智能体名称 | 核心职责 | 关键技能 (Tools/Skills) |
| --- | --- | --- |
| **1. 需求分析专家 (Discovery Agent)** | 引导用户细化想法，将一句“我想做...”变成具体的需求包。 | 提问引导、用户画像建模、痛点识别。 |
| **2. 深度访谈式调研专家 (Researcher Agent)** | 充当“专业信息挖掘者”，通过向用户提问引导其提供行业内幕、竞品情报或业务文档。 | 访谈式调研策略、对标分析、避坑指南、差异化建议。 |
| **3. 逻辑架构师 (Architect Agent)** | 将业务需求转化为底层逻辑。输出业务流程和功能清单。 | Mermaid 代码生成（画图）、信息架构设计。 |
| **4. 逻辑审计员 (Reviewer Agent)** | 扮演“杠精”开发，专门寻找逻辑漏洞和缺失的异常分支。 | 逻辑校验、边界情况 (Edge Cases) 模拟。 |
| **5. 文档专家 (Writer Agent)** | 整合所有信息，按照标准 PRD 模板输出文档。 | Markdown 格式化、专业术语转换、文档导出。 |

---

## 二、 架构模式：混合驱动 (Hybrid Workflow)

我们将采用 **三阶段顺序流 (Sequential)**，并在核心阶段嵌入 **层级协作 (Hierarchical)**。

### 阶段 1：需求对齐 (Sequential Phase 1)

* **参与者：** Discovery Agent
* **任务：** 1. 接收原始 Idea。
2. 通过 3-5 轮对话（Adaptive Interviewing）补全信息。
* **产出：** 《产品原始定义书》（包含：目标用户、核心场景、核心痛点）。

### 阶段 2：逻辑与可行性建模 (Hierarchical Sub-workflow)

这是最复杂的阶段，采用**层级模式**。由 **Architect Agent** 担任“组长（Manager）”。

1. **分发：** Architect Agent 将需求同步给 Researcher 和 Reviewer。
2. **协作：**
* **Researcher** 通过深度访谈反馈竞品做法、行业约束及用户反馈，输出《情报摘要》。
* **Architect** 生成初步流程图 (Mermaid)。
* **Reviewer** 审查流程图，指出“如果用户支付时断网了怎么办？”等问题。


3. **收敛：** Architect 吸收反馈，修正逻辑。

* **产出：** 《业务逻辑蓝图》（包含：业务流程图、功能矩阵、竞品对标）。

### 阶段 3：文档标准化 (Sequential Phase 3)

* **参与者：** Writer Agent
* **任务：** 将上一阶段确认的“蓝图”翻译成开发能读懂的 PRD。
* **产出：** 最终交付物 `Product_Requirement_Document.md`。

---

## 三、 工作流详细数据流转 (Data Flow)

为了让 Google ADK 正常运行，数据必须像接力棒一样传递：

1. **State Init:** 存储原始 Idea。
2. **State Update (Discovery):** 存入补全后的“产品定义”。
3. **Hierarchical Context (Logic Team):** * Architect 读取“产品定义”。
* Researcher 的访谈调研结果（对标分析、避坑指南）会被 Architect 引用。
* Reviewer 的修改意见被 Architect 记录并更新流程图。


4. **Final Payload:** Writer 读取最终的“业务逻辑蓝图”，将其格式化。

---

## 四、 关键交付物结构 (Deliverables)

智能体最终生成的文档应包含以下模块：

1. **文档信息：** 修订记录、项目背景。
2. **业务流程图：** 使用 Mermaid 渲染的逻辑图。
3. **核心功能说明：** 每一个功能点的输入、处理、输出逻辑。
4. **非功能性需求：** 性能要求、安全性、埋点需求。
5. **异常处理清单：** 由 Reviewer Agent 专门贡献的各类错误处理逻辑。
