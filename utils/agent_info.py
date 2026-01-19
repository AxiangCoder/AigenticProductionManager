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
        "instruction_path": "discovery_agent/discovery.md"
    }

    # 2. 逻辑架构师 (Architect Agent) - 你的核心 Agent
    ARCHITECT_AGENT = {
        "name": "Architect_Expert",
        "description": "核心逻辑转换器。负责将抽象想法转化为结构化业务逻辑、Mermaid流程图和功能清单。负责定义业务闭环路径。",
        "instruction_path": "architect_agent/architect.md"
    }

    # 3. 逻辑审计员 (Reviewer Agent)
    REVIEWER_AGENT = {
        "name": "Logic_Reviewer",
        "description": "质量把控专家。专门负责逻辑审查、漏洞发现和异常流程补充。用于对架构师产出的流程图进行边界案例（Edge Cases）压力测试。",
        "instruction_path": "reviewer_agent/reviewer.md"
    }

    # 4. 深度访谈式调研专家 (Researcher Agent)
    RESEARCHER_AGENT = {
        "name": "Market_Researcher",
        "description": "充当“专业信息挖掘者”，通过向用户提问引导其提供行业内幕、竞品情报或业务文档，从而为 Architect 提供决策支撑。",
        "instruction_path": "researcher_agent/researcher.md"
    }

    # 5. 文档专家 (Writer Agent)
    WRITER_AGENT = {
        "name": "PRD_Writer",
        "description": "交付物封装器。负责将各智能体协作产生的碎片化逻辑整理为专业、格式规范的 Markdown PRD 文档。",
        "instruction_path": "writer_agent/writer.md"
    }