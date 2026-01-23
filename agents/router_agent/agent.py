import json
from typing import AsyncGenerator
from pydantic import BaseModel
from google.adk.agents import Agent, BaseAgent
from google.adk.agents import InvocationContext
from google.adk.events import Event
from utils.load_prompt import load_prompt
from utils import MODEL, logger
from google.genai import types


class RouteDecision(BaseModel):
    """路由决策输出格式"""
    target_agent: str  # "discovery" | "research" | "continue" | "unknown"
    reason: str
    confidence: float  # 0.0-1.0


class RouterAgent(BaseAgent):
    """
    路由智能体：负责判断应该路由到哪个子智能体
    1. 分析用户输入和项目状态
    2. 判断应该路由到哪个智能体
    3. 包含首次判断逻辑
    """

    router: BaseAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        router = Agent(
            model=MODEL,
            name="Router_Agent",
            instruction=load_prompt("agents/router_agent/router.md"),
            output_key="router_output",
            output_schema=RouteDecision,  # 使用 output_schema 约束输出格式
            generate_content_config=types.GenerateContentConfig(
                temperature=0.3,  # 低温度，确保路由决策稳定
            ),
        )

        super().__init__(
            name="Router_Agent",
            description="智能路由决策器，负责判断应该路由到哪个子智能体",
            sub_agents=[router],
            router=router,
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
        
        将上下文信息存储到 state，router 会从 state 中读取
        """
        # 将上下文信息存储到 state
        ctx.session.state["_router_context"] = {
            "user_message": user_message,
            "project_stage": project_stage,
            "current_agent": current_agent,
        }
        
        # 调用路由智能体，获取 full_content
        full_content = ""
        async for event in self.router.run_async(ctx):
            if event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    full_content += part.text
        
        # 解析 JSON 输出
        decision_dict = self._parse_json(full_content)
        
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

    def _parse_json(self, text: str) -> dict:
        """
        加固版 JSON 解析：
        1. 使用非贪婪匹配 r'\{.*?\}' 只抓取第一个对象
        2. 增加对嵌套结构的容错
        """
        import json

        try:
            # 使用非贪婪匹配 (.*?)，只抓取从第一个 { 到它最近的一个 }
            # 但如果 JSON 内部有嵌套的花括号，非贪婪匹配会提前截断。
            # 所以最佳实践是：匹配所有，然后手动处理。

            # 找到第一个 {
            start_idx = text.find("{")
            if start_idx == -1:
                return {}

            # 找到对应的最后一个 } (针对并排 JSON，我们尝试找到第一个完整闭合的块)
            # 这里使用一个简单的计数器来寻找第一个完整的 JSON 对象
            content = text[start_idx:]
            bracket_count = 0
            end_idx = 0
            for i, char in enumerate(content):
                if char == "{":
                    bracket_count += 1
                elif char == "}":
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break

            if end_idx > 0:
                clean_json = content[:end_idx]
                return json.loads(clean_json)

            return {}
        except Exception as e:
            logger.error(f"JSON 解析极致加固失败: {e}")
            return {}

