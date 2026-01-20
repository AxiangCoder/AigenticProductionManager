from dataclasses import dataclass


@dataclass
class AgentInfo:
    """
    产品经理智能体应用 - 智能体注册表配置
    定义了每个智能体在 Google ADK 中的核心参数
    """

    # 1. 需求分析专家 (Discovery Agent)
    DISCOVERY_AGENT = {
        "name": "Discovery_Expert",
        "description": "负责产品启动阶段的需求挖掘与细化。当用户想法模糊、缺乏受众定义或痛点描述时调用。它通过引导式对话补全信息。",
        "instruction_path": "agents/discovery_agent/discovery.md",
        "output_key": "discovery_output"
    }

    # 2. 逻辑架构师 (Architect Agent) - 你的核心 Agent
    ARCHITECT_AGENT = {
        "name": "Architect_Expert",
        "description": "核心逻辑转换器。负责将抽象想法转化为结构化业务逻辑、Mermaid流程图和功能清单。负责定义业务闭环路径。",
        "instruction_path": "agents/architect_agent/architect.md",
        "output_key": "architect_output"
    }

    # 3. 逻辑审计员 (Reviewer Agent)
    REVIEWER_AGENT = {
        "name": "Logic_Reviewer",
        "description": "质量把控专家。专门负责逻辑审查、漏洞发现和异常流程补充。用于对架构师产出的流程图进行边界案例（Edge Cases）压力测试。",
        "instruction_path": "agents/reviewer_agent/reviewer.md",
        "output_key": "reviewer_output"
    }

    # 4. 深度访谈式调研专家 (Researcher Agent)
    RESEARCHER_AGENT = {
        "name": "Market_Researcher",
        "description": "充当“专业信息挖掘者”，通过向用户提问引导其提供行业内幕、竞品情报或业务文档，从而为 Architect 提供决策支撑。",
        "instruction_path": "agents/researcher_agent/researcher.md",
        "output_key": "researcher_output"
    }

    # 5. 文档专家 (Writer Agent)
    WRITER_AGENT = {
        "name": "PRD_Writer",
        "description": "交付物封装器。负责将各智能体协作产生的碎片化逻辑整理为专业、格式规范的 Markdown PRD 文档。",
        "instruction_path": "agents/writer_agent/writer.md",
        "output_key": "writer_output"
    }
    # 6. 首席产品专家 (Senior PM Agent)
    SENIOR_PM_AGENT = {
        "name": "Senior_PM_Auditor",
        "description": "质量决策专家与裁判。负责对各阶段产出进行深度逻辑审计与量化评分（JSON格式）。具备拦截机制，对不合格（<6分）的设计给出强制修改建议并触发迭代，确保产品方案具备商业深度与技术鲁棒性。",
        "instruction_path": "agents/senior_pm_agent/senior_pm.md",
        "output_key": "senior_pm_output"
    }

    # 7. 文档审计员与执行者 (Document Auditor Agent)
    DOCUMENT_AUDITOR_AGENT = {
        "name": "Document_Auditor",
        "description": "文档质量守门员。负责审查 Writer 产出的文档格式，并在合格后通过工具执行磁盘写入、更新或删除操作。它是文档落地的最后一道防线。",
        "instruction_path": "agents/document_auditor/auditor.md",
        "output_key": "auditor_output"
    }
