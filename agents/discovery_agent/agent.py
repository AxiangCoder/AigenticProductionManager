import json
from typing import AsyncGenerator
from google.adk.agents import Agent, LoopAgent, BaseAgent
from agents.senior_pm_agent import create_senior_pm_for
from google.adk.agents import InvocationContext
from google.adk.events import Event
from utils.load_prompt import load_prompt
from utils import MODEL, AgentInfo, logger


class DiscoveryPhaseAgent(BaseAgent):
    """
    自定义 Discovery 阶段智能体：
    1. 统一契约：PM 输出 JSON，代码解析。
    2. 后端过滤：屏蔽 JSON，给用户返回 human_message。
    3. 流程控制：代码通过 ctx.actions.escalate 控制退出，不再使用工具。
    """
    discovery_actor: BaseAgent
    senior_pm: BaseAgent
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self):
        discovery_actor = Agent(
            model=MODEL,
            name=AgentInfo.DISCOVERY_AGENT['name'],
            instruction=load_prompt(AgentInfo.DISCOVERY_AGENT['instruction_path']),
            output_key=AgentInfo.DISCOVERY_AGENT['output_key'],
        )
        # 工厂函数生成的 PM 指令中已包含目标 key
        senior_pm = create_senior_pm_for(AgentInfo.DISCOVERY_AGENT)
        
        super().__init__(
            name="Discovery_Phase_Manager",
            description="管理需求挖掘全过程：准入、对话、审计",
            sub_agents=[discovery_actor, senior_pm],
            discovery_actor=discovery_actor,
            senior_pm=senior_pm
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        output_key = AgentInfo.DISCOVERY_AGENT['output_key']
        pm_output_key = AgentInfo.SENIOR_PM_AGENT['output_key']

        # 初始化 state，解决模板渲染 KeyError
        if output_key not in ctx.session.state:
            ctx.session.state[output_key] = "执行者尚未产出阶段性总结。"

        is_sanity_passed = ctx.session.state.get("is_sanity_passed", False)
        
        # --- [阶段一]：职责 A - 需求准入验证 ---
        if not is_sanity_passed:
            logger.info(f"[{self.name}] CPO 正在静默审计需求准入...")
            
            # 捕获 PM 输出并手动解析
            full_content = ""
            async for event in self.senior_pm.run_async(ctx):
                if event.content and event.content.parts:
                    part = event.content.parts[0]
                    if hasattr(part, "text") and part.text:
                        full_content += part.text
            
            pm_report = self._parse_json(full_content)
            ctx.session.state[pm_output_key] = pm_report

            # 如果准入不通过，向用户显示温和引导
            if pm_report.get("verdict") == "REJECT":
                human_msg = pm_report.get("human_message", "我是 CPO 助手，请问有什么可以帮您？")
                yield Event(author="Senior_PM", content={"parts": [{"text": human_msg}]})
                return # 拦截，等待用户重新输入


        # --- [阶段二]：执行阶段 - 需求挖掘对话 ---
        discovery_output = ctx.session.state.get(output_key, "")
        has_finished_mining = "[Discovery_Expert] 需求挖掘已完成" in discovery_output

        if not has_finished_mining:
            async for event in self.discovery_actor.run_async(ctx):
                yield event
        else:
            # --- [阶段三]：职责 B - 质量审计 ---
            logger.info(f"[{self.name}] 检测到终产物，触发 CPO 质量审计...")
            
            full_content = ""
            async for event in self.senior_pm.run_async(ctx):
                if event.content and event.content.parts:
                    part = event.content.parts[0]
                    if hasattr(part, "text") and part.text:
                        full_content += part.text
            
            pm_report = self._parse_json(full_content)
            ctx.session.state[pm_output_key] = pm_report
            
            if pm_report.get("verdict") == "REJECT":
                system_ins = pm_report.get("system_instructions", "请继续完善。")
                yield Event(author="Senior_PM_Auditor", content={"parts": [{"text": f"审计未通过：{system_ins}"}]})
            else:
                score = pm_report.get("score", 0)
                if score >= 6:
                    yield Event(author="Senior_PM_Auditor", content={"parts": [{"text": f"CPO 审计通过 (得分: {score})。"}]})
                    ctx.actions.escalate = True # 代码控制流程跳转
                else:
                    yield Event(author="Senior_PM_Auditor", content={"parts": [{"text": f"得分 {score}，请继续优化。"}]})

    def _parse_json(self, text: str) -> dict:
        """安全解析 LLM 返回的 JSON"""
        try:
            clean_json = text.strip().strip('`').replace('json\n', '', 1)
            return json.loads(clean_json)
        except Exception as e:
            logger.info(f"JSON 解析失败: {e}")
            return {}

# 导出实例
discovery_phase_agent = DiscoveryPhaseAgent()