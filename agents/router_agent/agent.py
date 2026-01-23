import json
from typing import AsyncGenerator
from pydantic import BaseModel
from google.adk.agents import Agent, BaseAgent
from google.adk.agents import InvocationContext
from google.adk.events import Event
from utils.load_prompt import load_prompt
from utils import MODEL, logger, parse_json
from google.genai import types


class RouteDecision(BaseModel):
    """路由决策输出格式"""
    target_agent: str  # "discovery" | "research" | "continue" | "unknown"
    reason: str
    confidence: float  # 0.0-1.0
    instruction: str = ""  # 传递给子智能体的指令


class RouterAgent(BaseAgent):
    """
    路由智能体：负责判断应该路由到哪个子智能体
    1. 分析用户输入和项目状态
    2. 判断应该路由到哪个智能体
    3. 包含首次判断逻辑
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        super().__init__(
            name="Router_Agent",
            description="智能路由决策器，负责判断应该路由到哪个子智能体",
        )

    async def decide(
        self,
        ctx: InvocationContext,
        user_message: str,
        project_stage: str,
        current_agent: str | None,
    ) -> RouteDecision:
        """
        执行路由决策
        返回: RouteDecision 对象
        
        动态生成提示词并创建 router agent
        """
        # 加载提示词模板
        prompt_template = load_prompt("agents/router_agent/router.md")
        
        # 替换占位符
        current_agent_str = current_agent if current_agent else "None"
        instruction = prompt_template.replace("{user_message}", user_message) \
                                     .replace("{project_stage}", project_stage) \
                                     .replace("{current_agent}", current_agent_str)
        
        # 动态创建 router agent
        router = Agent(
            model=MODEL,
            name="Router_Agent",
            instruction=instruction,
            output_key="router_output",
            output_schema=RouteDecision,  # 使用 output_schema 约束输出格式
            generate_content_config=types.GenerateContentConfig(
                temperature=0.3,  # 低温度，确保路由决策稳定
            ),
        )
        
        # 调用路由智能体，获取 full_content
        full_content = ""
        async for event in router.run_async(ctx):
            if event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    full_content += part.text
        
        # 解析 JSON 输出
        decision_dict = parse_json(full_content)
        
        # 如果解析失败，尝试从 state 中读取（output_schema 可能会自动存储）
        if not decision_dict:
            router_output = ctx.session.state.get("router_output")
            if router_output:
                # 如果是 RouteDecision 对象，转换为字典
                if isinstance(router_output, RouteDecision):
                    decision_dict = router_output.dict()
                # 如果是字典，直接使用
                elif isinstance(router_output, dict):
                    decision_dict = router_output
                # 如果是字符串，尝试解析 JSON
                elif isinstance(router_output, str):
                    try:
                        decision_dict = json.loads(router_output)
                    except Exception as e:
                        logger.error(f"[{self.name}] 解析 state 中的 router_output 失败: {e}")
        
        # 如果仍然解析失败，返回默认决策
        if not decision_dict:
            logger.warning(f"[{self.name}] 无法解析路由决策，返回默认决策")
            return RouteDecision(
                target_agent="unknown",
                reason="无法解析路由决策",
                confidence=0.0,
            )
        
        # 返回路由决策
        return RouteDecision(
            target_agent=decision_dict.get("target_agent", "unknown"),
            reason=decision_dict.get("reason", ""),
            confidence=decision_dict.get("confidence", 0.0),
            instruction=decision_dict.get("instruction", ""),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        路由智能体的主执行逻辑
        注意：这个智能体通常不直接运行，而是通过 decide() 方法被调用
        """
        # 如果直接运行，返回提示信息
        yield Event(
            author=self.name,
            content={
                "parts": [
                    {
                        "text": "路由智能体应该通过 decide() 方法调用，而不是直接运行。"
                    }
                ]
            },
        )


