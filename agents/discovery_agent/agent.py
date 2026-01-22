import json
from typing import AsyncGenerator
from google.adk.agents import Agent, BaseAgent
from agents.senior_pm_agent import create_senior_pm_for
from agents.document_auditor import create_document_auditor
from google.adk.agents import InvocationContext
from google.adk.events import Event, EventActions
from utils.load_prompt import load_prompt
from utils import MODEL, AgentInfo, logger
from google.genai import types


class DiscoveryPhaseAgent(BaseAgent):
    """
    自定义 Discovery 阶段智能体：
    1. 统一契约：PM 输出 JSON，代码解析。
    2. 后端过滤：屏蔽 JSON，给用户返回 human_message。
    3. 流程控制：通过 return 控制退出，状态更新使用 EventActions.state_delta。
    """

    discovery_actor: BaseAgent
    senior_pm: BaseAgent
    doc_auditor: BaseAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self):
        discovery_actor = Agent(
            model=MODEL,
            name=AgentInfo.DISCOVERY_AGENT["name"],
            instruction=load_prompt(AgentInfo.DISCOVERY_AGENT["instruction_path"]),
            output_key=AgentInfo.DISCOVERY_AGENT["output_key"],
            generate_content_config=types.GenerateContentConfig(
                temperature=0.9,
            ),
        )
        # 工厂函数生成的 PM 指令中已包含目标 key
        senior_pm = create_senior_pm_for(AgentInfo.DISCOVERY_AGENT)
        # 使用工厂函数创建独立的 document_auditor 实例
        doc_auditor = create_document_auditor()

        super().__init__(
            name="Discovery_Phase_Manager",
            description="管理需求挖掘全过程：准入、对话、审计、文档归档",
            sub_agents=[discovery_actor, senior_pm, doc_auditor],
            discovery_actor=discovery_actor,
            senior_pm=senior_pm,
            doc_auditor=doc_auditor,
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        output_key = AgentInfo.DISCOVERY_AGENT["output_key"]

        # 1. 基础状态获取
        is_sanity_passed = ctx.session.state.get("is_sanity_passed", False)

        # 初始化 state，解决模板渲染 KeyError
        if output_key not in ctx.session.state:
            ctx.session.state[output_key] = "执行者尚未产出阶段性总结。"

        logger.debug(f"is_sanity_passed: {is_sanity_passed}")

        # --- [阶段一]：职责 A - 需求准入验证 ---
        if not is_sanity_passed:
            async for event in self._stage_sanity_check(ctx=ctx, output_key=output_key):
                yield event
            if not ctx.session.state.get("is_sanity_passed", False):
                return  # 拦截，等待用户重新输入

        # --- [阶段二]：执行阶段 - 需求挖掘与用户确认 ---
        async for event in self._stage_discovery_mining(ctx=ctx):
            yield event

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

    async def _stage_sanity_check(
        self, *, ctx: InvocationContext, output_key
    ) -> AsyncGenerator[Event, None]:

        logger.info(f"[{self.name}] CPO 正在静默审计需求准入...")

        full_content = ""
        yield Event(
            author=self.name,
            content={"parts": [{"text": "正在审计需求准入...\n\n"}]},
        )
        async for event in self.senior_pm.run_async(ctx):
            if event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    full_content += part.text

        pm_report = self._parse_json(full_content)

        # 如果准入不通过，向用户显示温和引导
        if pm_report.get("verdict") == "REJECT":
            human_msg = pm_report.get(
                "human_message", "我是 CPO 助手，请问有什么可以帮您？"
            )
            yield Event(
                author=self.name,
                content={"parts": [{"text": human_msg}]},
                actions=EventActions(state_delta={output_key: pm_report}),
            )
        else:
            yield Event(
                author=self.name,
                content={"parts": [{"text": "需求合法，已转交给需求专家为您服务。\n\n"}]},
                actions=EventActions(
                    state_delta={
                        "is_sanity_passed": True,
                    }
                ),
            )

    async def _stage_discovery_mining(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """阶段二：需求挖掘与用户确认"""
        # 1. 挖掘、展示、确认判断逻辑 ...
        async for event in self._discover_agent_confirm_user_needs(ctx=ctx):
            yield event

        # 2. 进入审计
        if ctx.session.state.get("user_confirmed", False):
            async for event in self._pm_agent_quality_audit(
                ctx=ctx
            ):
                yield event

    async def _discover_agent_confirm_user_needs(
        self, *, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        full_content = ""
        async for event in self.discovery_actor.run_async(ctx):
            if event.content and event.content.parts:
                part = event.content.parts[0]
                if hasattr(part, "text") and part.text:
                    full_content += part.text
            # if event.content.parts[0].text == full_content and full_content:
            #     # 跳过这个重复的完整内容 event
            #     logger.debug(f"[{self.name}] 跳过 streaming 模式下的重复完整内容 event")
            #     continue
            logger.debug (f"text: {event.content.parts[0].text}")
            logger.debug(f"是否结束：{event.is_final_response()}")
            yield event

        # 1. 进入用户确认阶段
        if "[Discovery_Expert] 需求挖掘已完成" in full_content:
            logger.info(f"[{self.name}] 检测到挖掘完成标记，展示总结并引导用户确认...")
            yield Event(
                author=self.name,
                content={
                    "parts": [
                        {
                            "text": f"**请确认以上需求总结是否准确。如果确认无误，请回复“确认”或“继续”。如需修改，请直接说明需要调整的内容。**"
                        }
                    ]
                },
                actions=EventActions(state_delta={"user_confirmed": False}),
            )
            return
        # 2. 用户要求修改阶段
        if "[Discovery_Expert] 用户要求修改" in full_content:
            yield Event(
                author=self.name,
                content={"parts": [{"text": "好的，正在根据您的意见进行调整..."}]},
                actions=EventActions(state_delta={"user_confirmed": False}),
            )
            async for event in self._discover_agent_confirm_user_needs(ctx=ctx):
                yield event

        # 3. 用户已确认，交由审计阶段
        if "[Discovery_Expert] 用户已确认" in full_content:
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
        # 1. 审计通过，进入文档归档阶段
        if (pm_report.get("verdict") == "PASS" and pm_report.get("score") >= 6) or ctx.session.state.get("feedback_count", 0) >= 3:
            async for event in self._document_archive(
                ctx=ctx, score=pm_report.get("score", 0)
            ):
                yield event
            return


        # 2. 审计未通过，返回反馈
        system_ins = pm_report.get("system_instructions", "请继续完善。")
        score = pm_report.get("score", 0)
        audit_feedback_text = (
            f"CPO 审计未通过（得分 {score}）。反馈如下：\n\n{system_ins}\n\n"
        )
        yield Event(
            author=self.name,
            content={"parts": [{"text": f"重新生成文档中...\n\n{audit_feedback_text}\n\n"}]},
            actions=EventActions(
                state_delta={
                    "user_confirmed": False,  # 回到未确认状态
                    "audit_feedback": audit_feedback_text,  # 将反馈注入 state
                    "feedback_count": ctx.session.state.get("feedback_count", 0) + 1
                }
            ),
        )
        async for event in self._discover_agent_confirm_user_needs(ctx=ctx):
            yield event

    async def _document_archive(
        self, *, ctx: InvocationContext, score: int
    ) -> AsyncGenerator[Event, None]:
        """
        文档生成阶段，进入这个阶段一定会生成文档，只是可能会审计次数过多需要用户手动优化：
        1. 审计通过，进入文档归档阶段
        2. 审计通过次数过多，返回反馈
        """
        if score >= 6:
            text = f"CPO 审计通过 (得分: {score})。正在申请文档归档...\n\n"
        else:
            text = f"CPO 审计通过次数过多（{ctx.session.state.get('feedback_count', 0)}次），得分 {score}，请手动优化。\n\n"
        yield Event(
            author=self.name,
            content={
                "parts": [
                    {"text": text}
                ]
            },
        )
        async for event in self.doc_auditor.run_async(ctx):
            yield event
        return  # 流程结束


# 导出实例
discovery_phase_agent = DiscoveryPhaseAgent()
