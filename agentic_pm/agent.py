import os
from typing import AsyncGenerator, Optional
from google.adk.agents import BaseAgent
from agents.discovery_agent import DiscoveryPhaseAgent
from agents.researcher_agent import ResearchPhaseAgent
from agents.router_agent import RouterAgent
from google.adk.agents import InvocationContext
from google.adk.events import Event, EventActions
from utils import logger


class AgenticPMAgent(BaseAgent):
    """
    主智能体：负责路由决策、项目阶段管理、用户交互
    1. 项目阶段检测：检查 outputs 目录判断当前项目阶段
    2. 友好问候：首次加载时根据项目阶段友好问候用户
    3. 智能路由：使用 RouterAgent 进行路由决策（包含首次判断）
    4. 状态管理：管理当前活跃智能体和项目阶段
    """

    discovery_agent: BaseAgent
    research_agent: BaseAgent
    router_agent: BaseAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        # 初始化子智能体
        discovery_agent = DiscoveryPhaseAgent()
        research_agent = ResearchPhaseAgent()
        router_agent = RouterAgent()

        super().__init__(
            name="Agentic_PM",
            description="智能产品经理助手，负责路由决策和用户交互",
            sub_agents=[discovery_agent, research_agent, router_agent],
            discovery_agent=discovery_agent,
            research_agent=research_agent,
            router_agent=router_agent,
        )

    def _detect_project_stage(self) -> str:
        """
        检查 outputs 目录，判断当前项目阶段
        返回: "discovery" | "research" | "unknown"
        """
        output_dir = "outputs"
        
        # 检查 outputs 目录是否存在
        if not os.path.exists(output_dir):
            logger.info(f"[{self.name}] outputs 目录不存在，判断为 discovery 阶段")
            return "discovery"
        
        # 扫描 outputs 目录下的 .md 文件
        try:
            files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
        except Exception as e:
            logger.error(f"[{self.name}] 读取 outputs 目录失败: {e}")
            return "unknown"
        
        if not files:
            logger.info(f"[{self.name}] outputs 目录为空，判断为 discovery 阶段")
            return "discovery"
        
        # 检查是否有 Discovery 相关文档（PRD、Discovery 输出等）
        has_discovery_doc = any(
            "prd" in f.lower() or "discovery" in f.lower() 
            for f in files
        )
        
        # 检查是否有 Research 相关文档
        has_research_doc = any(
            "research" in f.lower() or "调研" in f.lower()
            for f in files
        )
        
        # 判断逻辑
        if has_discovery_doc and not has_research_doc:
            logger.info(f"[{self.name}] 检测到 Discovery 文档但无 Research 文档，判断为 research 阶段")
            return "research"
        elif not has_discovery_doc:
            logger.info(f"[{self.name}] 未检测到 Discovery 文档，判断为 discovery 阶段")
            return "discovery"
        else:
            logger.info(f"[{self.name}] 检测到多个阶段文档，判断为 unknown")
            return "unknown"

    def _is_first_load(self, ctx: InvocationContext) -> bool:
        """
        检测是否是首次加载（需要友好问候）
        """
        # 检查是否已经问候过
        if ctx.session.state.get("_has_greeted", False):
            return False
        
        # 检查事件历史中是否有智能体回复（排除系统消息）
        agent_events = [
            e for e in ctx.session.events
            if e.author != "user" and e.author != "system"
        ]
        
        return len(agent_events) == 0

    def _get_last_user_message(self, ctx: InvocationContext) -> str:
        """
        从事件历史中提取最新用户消息
        """
        for event in reversed(ctx.session.events):
            if event.author == "user" and event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    return part.text.strip()
        return ""

    def _get_greeting_message(self, project_stage: str) -> str:
        """
        根据项目阶段生成问候消息
        """
        greetings = {
            "discovery": "你好！我是你的产品经理助手。看起来你还没有开始产品设计，你想从哪个想法开始呢？",
            "research": "你好！我看到你已经完成了需求分析，现在想进行市场调研吗？还是有其他需求？",
            "unknown": "你好！我是你的产品经理助手。你想从哪个阶段开始呢？",
        }
        return greetings.get(project_stage, greetings["unknown"])

    async def _greet_user(
        self, ctx: InvocationContext, project_stage: str
    ) -> AsyncGenerator[Event, None]:
        """
        友好问候用户
        """
        greeting = self._get_greeting_message(project_stage)
        
        yield Event(
            author=self.name,
            content={"parts": [{"text": greeting}]},
            actions=EventActions(
                state_delta={
                    "_has_greeted": True,
                    "project_stage": project_stage,
                }
            ),
        )

    def _get_agent(self, agent_name: str) -> BaseAgent:
        """
        根据名称获取对应的智能体实例
        """
        agent_map = {
            "discovery": self.discovery_agent,
            "research": self.research_agent,
        }
        return agent_map.get(agent_name, self.discovery_agent)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        主执行逻辑
        """
        # 1. 检测项目阶段
        project_stage = self._detect_project_stage()
        logger.info(f"[{self.name}] 检测到项目阶段: {project_stage}")
        
        # 2. 首次加载：友好问候
        if self._is_first_load(ctx):
            async for event in self._greet_user(ctx, project_stage):
                yield event
            return  # 等待用户输入
        
        # 3. 获取用户输入
        last_user_msg = self._get_last_user_message(ctx)
        if not last_user_msg:
            logger.warning(f"[{self.name}] 未获取到用户消息")
            return
        
        # 4. 获取当前活跃智能体
        current_agent_name = ctx.session.state.get("current_agent", None)
        
        # 5. 使用 RouterAgent 进行路由决策（包含首次判断）
        route_decision = await self.router_agent.decide(
            ctx=ctx,
            user_message=last_user_msg,
            project_stage=project_stage,
            current_agent=current_agent_name,
        )
        
        logger.info(
            f"[{self.name}] 路由决策: {route_decision.target_agent} "
            f"(原因: {route_decision.reason}, 置信度: {route_decision.confidence})"
        )
        
        # 6. 处理路由决策
        if route_decision.target_agent == "unknown":
            # 无法确定，友好询问用户
            yield Event(
                author=self.name,
                content={
                    "parts": [
                        {
                            "text": "抱歉，我无法确定应该由哪个智能体处理您的请求。请明确说明您的需求，例如：\n"
                            "- 如果是新想法或需求分析，请说\"新需求\"或\"需求分析\"\n"
                            "- 如果是市场调研，请说\"市场调研\"或\"竞品分析\""
                        }
                    ]
                },
            )
            return
        
        # 7. 确定目标智能体
        if route_decision.target_agent == "continue":
            # 继续当前智能体
            if current_agent_name:
                target_agent_name = current_agent_name
            else:
                # 如果没有当前智能体，默认路由到 discovery
                target_agent_name = "discovery"
                logger.warning(f"[{self.name}] 路由决策为 continue 但没有当前智能体，默认路由到 discovery")
        else:
            # 路由到指定智能体
            target_agent_name = route_decision.target_agent
        
        # 8. 更新状态（如果需要切换智能体）
        if target_agent_name != current_agent_name:
            logger.info(
                f"[{self.name}] 路由切换: {current_agent_name} -> {target_agent_name}"
            )
            # 友好的切换提示
            agent_names = {
                "discovery": "需求分析",
                "research": "市场调研",
            }
            target_name_cn = agent_names.get(target_agent_name, target_agent_name)
            
            # 如果是首次路由（current_agent_name 为 None），不显示切换提示
            if current_agent_name is not None:
                yield Event(
                    author=self.name,
                    content={
                        "parts": [
                            {
                                "text": f"正在切换到 {target_name_cn} 阶段...\n\n"
                            }
                        ]
                    },
                    actions=EventActions(
                        state_delta={"current_agent": target_agent_name}
                    ),
                )
            else:
                # 首次路由，静默设置状态
                yield Event(
                    author=self.name,
                    content={"parts": []},  # 空内容，不显示
                    actions=EventActions(
                        state_delta={"current_agent": target_agent_name}
                    ),
                )
        
        # 9. 调用子智能体
        target_agent = self._get_agent(target_agent_name)
        async for event in target_agent.run_async(ctx):
            yield event


# 导出实例（ADK 需要 root_agent 变量）
root_agent = AgenticPMAgent()
