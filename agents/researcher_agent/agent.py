from typing import AsyncGenerator
from google.adk.agents import Agent, BaseAgent
from agents.senior_pm_agent import create_senior_pm_for
from google.adk.agents import InvocationContext
from google.adk.events import Event, EventActions
from utils.load_prompt import load_prompt
from utils import MODEL, AgentInfo, logger, parse_json, find_latest_document
from google.genai import types


class ResearchPhaseAgent(BaseAgent):
    """
    自定义 Research 阶段智能体：
    1. 统一契约：PM 输出 JSON，代码解析。
    2. 后端过滤：屏蔽 JSON，给用户返回 human_message。
    3. 流程控制：通过 return 控制退出，状态更新使用 EventActions.state_delta。
    """

    researcher_actor: BaseAgent
    senior_pm: BaseAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        researcher_actor = Agent(
            model=MODEL,
            name=AgentInfo.RESEARCHER_AGENT["name"],
            instruction=load_prompt(AgentInfo.RESEARCHER_AGENT["instruction_path"]),
            output_key=AgentInfo.RESEARCHER_AGENT["output_key"],
            generate_content_config=types.GenerateContentConfig(
                temperature=0.7,
            ),
        )
        # 工厂函数生成的 PM 指令中已包含目标 key
        senior_pm = create_senior_pm_for(AgentInfo.RESEARCHER_AGENT)

        super().__init__(
            name="Research_Phase_Manager",
            description="管理市场调研全过程：访谈、确认、审计",
            sub_agents=[researcher_actor, senior_pm],
            researcher_actor=researcher_actor,
            senior_pm=senior_pm,
        )

    def _load_discovery_document(self) -> str:
        """
        从 outputs 目录加载 Discovery Agent 输出的文档
        返回文档内容，如果不存在则返回空字符串
        """
        doc_content = find_latest_document(
            output_dir="outputs",
            keywords=["discovery", "PRD"],
            agent_name=self.name
        )
        return doc_content if doc_content else ""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        output_key = AgentInfo.RESEARCHER_AGENT["output_key"]

        # 1. 加载 Discovery 文档（独立智能体，不依赖之前的 state 和 chat）
        discovery_doc = self._load_discovery_document()
        
        # 2. 将文档内容注入到 state，供 researcher_actor 使用
        # 使用一个专门的 key 存储 Discovery 文档内容
        discovery_doc_key = "_discovery_document_content"
        ctx.session.state[discovery_doc_key] = discovery_doc if discovery_doc else "（未找到 Discovery 文档）"
        
        # 3. 初始化 state，解决模板渲染 KeyError
        if output_key not in ctx.session.state:
            ctx.session.state[output_key] = "执行者尚未产出阶段性总结。"
        
        # 4. 重置调研相关的状态（独立智能体，不依赖之前的 state）
        ctx.session.state["user_confirmed"] = False
        ctx.session.state["audit_feedback"] = ""
        ctx.session.state["feedback_count"] = 0

        # 5. 将 Discovery 文档内容注入到对话中（独立智能体，文档作为对话的起始）
        # 由于 LLM 只能看到聊天历史，我们需要将文档内容作为对话的一部分
        # 虽然这会在对话历史中添加内容，但这是让独立智能体获取文档的唯一方式
        if discovery_doc:
            # 将文档内容作为系统消息注入，让 researcher_actor 能够读取
            yield Event(
                author="system",
                content={"parts": [{"text": f"以下是 Discovery 阶段输出的产品定义文档：\n\n{discovery_doc}\n\n---\n\n请基于以上文档内容进行市场调研。"}]},
            )
            yield Event(
                author=self.name,
                content={"parts": [{"text": f"已加载 Discovery 阶段的产品定义文档，开始进行市场调研...\n\n"}]},
            )
        else:
            yield Event(
                author=self.name,
                content={"parts": [{"text": f"警告：未找到 Discovery 文档，将基于当前对话进行调研。\n\n"}]},
            )

        # --- 执行阶段：市场调研与用户确认 ---
        async for event in self._stage_research_interview(ctx=ctx):
            yield event

    def _parse_json(self, text: str) -> dict:
        """
        使用公共的 parse_json 工具函数解析 JSON
        """
        return parse_json(text)

    async def _stage_research_interview(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """阶段：市场调研与用户确认"""
        # 1. 调研、展示、确认判断逻辑
        async for event in self._researcher_confirm_user_needs(ctx=ctx):
            yield event

        # 2. 进入审计
        if ctx.session.state.get("user_confirmed", False):
            async for event in self._pm_agent_quality_audit(ctx=ctx):
                yield event

    async def _researcher_confirm_user_needs(
        self, *, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        full_content = ""
        async for event in self.researcher_actor.run_async(ctx):
            if event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    full_content += part.text
            yield event

        # 1. 进入用户确认阶段
        if "[Market_Researcher] 市场调研已完成" in full_content:
            logger.info(f"[{self.name}] 检测到调研完成标记，展示总结并引导用户确认...")
            yield Event(
                author=self.name,
                content={
                    "parts": [
                        {
                            "text": f"**请确认以上调研总结是否准确。如果确认无误，请回复确认或继续。如需修改，请直接说明需要调整的内容。**"
                        }
                    ]
                },
                actions=EventActions(state_delta={"user_confirmed": False}),
            )
            return
        # 2. 用户要求修改阶段
        if "[Market_Researcher] 用户要求修改" in full_content:
            yield Event(
                author=self.name,
                content={"parts": [{"text": "好的，正在根据您的意见进行调整..."}]},
                actions=EventActions(state_delta={"user_confirmed": False}),
            )
            async for event in self._researcher_confirm_user_needs(ctx=ctx):
                yield event

        # 3. 用户已确认，交由审计阶段
        if "[Market_Researcher] 用户已确认" in full_content:
            yield Event(
                author=self.name,
                content={"parts": [{"text": "收到确认，正在提交 CPO 进行最终审计...\n\n"}]},
                actions=EventActions(state_delta={"user_confirmed": True}),
            )

    async def _pm_agent_quality_audit(
        self, *, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        full_content = ""
        async for event in self.senior_pm.run_async(ctx):
            if event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    full_content += part.text
        pm_report = self._parse_json(full_content)
        
        # 1. 审计通过
        if pm_report.get("verdict") == "PASS" and pm_report.get("score", 0) >= 6:
            yield Event(
                author=self.name,
                content={
                    "parts": [
                        {
                            "text": f"CPO 审计通过 (得分: {pm_report.get('score', 0)})。调研结果已准备就绪，可进入架构设计阶段。\n\n"
                        }
                    ]
                },
            )
            return

        # 2. 审计未通过，返回反馈
        system_ins = pm_report.get("system_instructions", "请继续完善。")
        score = pm_report.get("score", 0)
        audit_feedback_text = (
            f"CPO 审计未通过（得分 {score}）。反馈如下：\n\n{system_ins}\n\n"
        )
        yield Event(
            author=self.name,
            content={"parts": [{"text": f"重新生成调研报告中...\n\n{audit_feedback_text}\n\n"}]},
            actions=EventActions(
                state_delta={
                    "user_confirmed": False,  # 回到未确认状态
                    "audit_feedback": audit_feedback_text,  # 将反馈注入 state
                    "feedback_count": ctx.session.state.get("feedback_count", 0) + 1
                }
            ),
        )
        async for event in self._researcher_confirm_user_needs(ctx=ctx):
            yield event


# 导出实例
research_phase_agent = ResearchPhaseAgent()
