import logging
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.agents import InvocationContext

from discovery_agent.agent import discovery_agent
from architect_agent.agent import architect_agent
from researcher_agent.agent import researcher_agent
from reviewer_agent.agent import reviewer_agent
from writer_agent.agent import writer_agent

# 配置日志
logger = logging.getLogger(__name__)

class PMAgentCenter(BaseAgent):
    """
    自定义智能体：虚拟产研中心 (PM Agent Center)
    
    实现 README.md 中描述的“混合驱动 (Hybrid Workflow)”架构：
    1. 阶段 1 (Sequential): Discovery Agent 进行需求挖掘
    2. 阶段 2 (Custom Logic): 逻辑与可行性建模 (Researcher -> Architect -> Reviewer -> Architect)
    3. 阶段 3 (Sequential): Writer Agent 输出标准化 PRD
    """

    discovery_agent: BaseAgent
    researcher_agent: BaseAgent
    architect_agent: BaseAgent
    reviewer_agent: BaseAgent
    writer_agent: BaseAgent

    # 允许 Pydantic 处理自定义类类型
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, name="PM_Agent_Center"):
        # 定义所有参与的子智能体
        sub_agents = [
            discovery_agent,
            researcher_agent,
            architect_agent,
            reviewer_agent,
            writer_agent
        ]
        
        super().__init__(
            name=name,
            description="虚拟产研中心：从模糊想法到全套 PRD 的产出",
            sub_agents=sub_agents,
            # 将智能体实例传入 super().__init__ 以通过 Pydantic 校验
            discovery_agent=discovery_agent,
            researcher_agent=researcher_agent,
            architect_agent=architect_agent,
            reviewer_agent=reviewer_agent,
            writer_agent=writer_agent
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        核心编排逻辑
        """
        logger.info(f"[{self.name}] 启动虚拟产研工作流...")

        # ==========================================
        # 阶段 1：需求对齐 (Discovery Phase)
        # ==========================================
        logger.info(f"[{self.name}] === 进入阶段 1：需求对齐 (Discovery) ===")
        async for event in self.discovery_agent.run_async(ctx):
            yield event
            
        # 检查是否已有产品定义 (这里假设 Discovery Agent 会更新 Session State)
        # 实际开发中可以通过检查 key 是否存在来决定是否中断，这里先继续

        # ==========================================
        # 阶段 2：逻辑与可行性建模 (Logic & Feasibility Phase)
        # ==========================================
        logger.info(f"[{self.name}] === 进入阶段 2：逻辑与可行性建模 (Logic Team) ===")
        
        # 2.1 市场/竞品调研 (Researcher) - 为架构设计提供事实依据
        logger.info(f"[{self.name}] Step 2.1: Researcher 进行访谈与调研...")
        async for event in self.researcher_agent.run_async(ctx):
            yield event

        # 2.2 初步架构设计 (Architect - Draft)
        logger.info(f"[{self.name}] Step 2.2: Architect 输出初步逻辑蓝图...")
        async for event in self.architect_agent.run_async(ctx):
            yield event

        # 2.3 逻辑审计 (Reviewer) - 寻找漏洞
        logger.info(f"[{self.name}] Step 2.3: Reviewer 进行逻辑审计与压力测试...")
        async for event in self.reviewer_agent.run_async(ctx):
            yield event

        # 2.4 架构修正 (Architect - Finalize) - 根据审计意见完善设计
        # 只有在 Reviewer 提出重大修改建议时才需要（这里简化为总是执行一次修正闭环）
        logger.info(f"[{self.name}] Step 2.4: Architect 根据审计意见进行最终修正...")
        async for event in self.architect_agent.run_async(ctx):
            yield event

        # ==========================================
        # 阶段 3：文档标准化 (Documentation Phase)
        # ==========================================
        logger.info(f"[{self.name}] === 进入阶段 3：文档标准化 (Documentation) ===")
        async for event in self.writer_agent.run_async(ctx):
            yield event

        logger.info(f"[{self.name}] 工作流结束。")

# 实例化应用智能体
root_agent = PMAgentCenter()
