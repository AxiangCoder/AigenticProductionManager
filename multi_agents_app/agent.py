import logging
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.agents import InvocationContext

from agents import discovery_agent
from agents import architect_agent
from agents import researcher_agent
from agents import reviewer_agent
from agents import writer_agent
from agents import discovery_loop_agent

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
            # discovery_agent,
            discovery_loop_agent,
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
            # discovery_agent=discovery_agent,
            discovery_agent=discovery_loop_agent,
            researcher_agent=researcher_agent,
            architect_agent=architect_agent,
            reviewer_agent=reviewer_agent,
            writer_agent=writer_agent
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        核心编排逻辑，支持人机交互 (HITL)
        """
        logger.info(f"[{self.name}] 启动虚拟产研工作流...")

        # 检查用户是否发送了“继续”指令，用于自动更新审批状态
        last_user_msg = ""
        for event in reversed(ctx.session.events):
            if event.author == "user" and event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    last_user_msg = part.text.strip()
                    break
        
        if "继续" in last_user_msg:
            current_workflow_step = ctx.session.state.get("workflow_step")
            if current_workflow_step == "discovery_check":
                ctx.session.state["discovery_approved"] = True
                logger.info(f"[{self.name}] 收到人工指令：确认需求阶段，准备进入下一阶段。")
            elif current_workflow_step == "logic_check":
                ctx.session.state["logic_approved"] = True
                logger.info(f"[{self.name}] 收到人工指令：确认架构阶段，准备输出文档。")

        # 获取当前进度
        current_step = ctx.session.state.get("workflow_step", "discovery")

        # ==========================================
        # 阶段 1：需求对齐 (Discovery Phase)
        # ==========================================
        if current_step == "discovery":
            logger.info(f"[{self.name}] === 进入阶段 1：需求对齐 (Discovery) ===")
            async for event in self.discovery_agent.run_async(ctx):
                yield event
            
            # 标记该阶段完成，进入人工确认
            ctx.session.state["workflow_step"] = "discovery_check"
            current_step = "discovery_check"

        # --- 人工确认点：需求确认 ---
        if current_step == "discovery_check":
            approval = ctx.session.state.get("discovery_approved", False)
            if not approval:
                logger.info(f"[{self.name}] 等待人工确认需求挖掘结果...")
                yield Event(
                    author=self.name, 
                    content="[HITL] 阶段 1 (需求挖掘) 已完成。请检查以上产出并确认。输入 '继续' 或在系统中设置 'discovery_approved=True' 以继续。"
                )
                return # 中断执行，等待下次运行
            
            ctx.session.state["workflow_step"] = "logic_feasibility"
            current_step = "logic_feasibility"

        # ==========================================
        # 阶段 2：逻辑与可行性建模 (Logic & Feasibility Phase)
        # ==========================================
        if current_step == "logic_feasibility":
            logger.info(f"[{self.name}] === 进入阶段 2：逻辑与可行性建模 (Logic Team) ===")
            
            # 2.1 市场/竞品调研 (Researcher)
            logger.info(f"[{self.name}] Step 2.1: Researcher 进行访谈与调研...")
            async for event in self.researcher_agent.run_async(ctx):
                yield event

            # 2.2 初步架构设计 (Architect - Draft)
            logger.info(f"[{self.name}] Step 2.2: Architect 输出初步逻辑蓝图...")
            async for event in self.architect_agent.run_async(ctx):
                yield event

            # 2.3 逻辑审计 (Reviewer)
            logger.info(f"[{self.name}] Step 2.3: Reviewer 进行逻辑审计与压力测试...")
            async for event in self.reviewer_agent.run_async(ctx):
                yield event

            # 2.4 架构修正 (Architect - Finalize)
            logger.info(f"[{self.name}] Step 2.4: Architect 根据审计意见进行最终修正...")
            async for event in self.architect_agent.run_async(ctx):
                yield event
            
            ctx.session.state["workflow_step"] = "logic_check"
            current_step = "logic_check"

        # --- 人工确认点：架构确认 ---
        if current_step == "logic_check":
            approval = ctx.session.state.get("logic_approved", False)
            if not approval:
                logger.info(f"[{self.name}] 等待人工确认架构设计结果...")
                yield Event(
                    author=self.name, 
                    content="[HITL] 阶段 2 (逻辑与架构) 已完成。请检查架构图与审计建议。确认无误后请回复 '继续'。"
                )
                return
            
            ctx.session.state["workflow_step"] = "documentation"
            current_step = "documentation"

        # ==========================================
        # 阶段 3：文档标准化 (Documentation Phase)
        # ==========================================
        if current_step == "documentation":
            logger.info(f"[{self.name}] === 进入阶段 3：文档标准化 (Documentation) ===")
            async for event in self.writer_agent.run_async(ctx):
                yield event
            
            ctx.session.state["workflow_step"] = "completed"
            logger.info(f"[{self.name}] 工作流全部结束。")

# 实例化应用智能体
root_agent = PMAgentCenter()
