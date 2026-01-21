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
            name=AgentInfo.DISCOVERY_AGENT['name'],
            instruction=load_prompt(AgentInfo.DISCOVERY_AGENT['instruction_path']),
            output_key=AgentInfo.DISCOVERY_AGENT['output_key'],
            generate_content_config=types.GenerateContentConfig(
                temperature=0.9,
            )
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
            doc_auditor=doc_auditor
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        output_key = AgentInfo.DISCOVERY_AGENT['output_key']
        pm_output_key = AgentInfo.SENIOR_PM_AGENT['output_key']

        # 1. 基础状态获取
        discovery_output = ctx.session.state.get(output_key, "")
        is_sanity_passed = ctx.session.state.get("is_sanity_passed", False)
        summary_shown = ctx.session.state.get("summary_shown", False)
        user_confirmed = ctx.session.state.get("user_confirmed", False)
        audit_feedback = ctx.session.state.get("audit_feedback", "")

        try:
            state_json = json.dumps(dict(ctx.session.state), indent=2, ensure_ascii=False)
            logger.debug(f"[Session State]\n{state_json}")
        except TypeError:
            logger.debug (f"ctx.session.state: {ctx.session.state}")

        # 初始化 state，解决模板渲染 KeyError
        if output_key not in ctx.session.state:
            ctx.session.state[output_key] = "执行者尚未产出阶段性总结。"

        is_sanity_passed = ctx.session.state.get("is_sanity_passed", False)

        logger.debug (f"is_sanity_passed: {is_sanity_passed}")
        
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

            # 如果准入不通过，向用户显示温和引导
            if pm_report.get("verdict") == "REJECT":
                human_msg = pm_report.get("human_message", "我是 CPO 助手，请问有什么可以帮您？")
                yield Event(
                    author="Senior_PM", 
                    content={"parts": [{"text": human_msg}]},
                    actions=EventActions(state_delta={pm_output_key: pm_report})
                )
                return # 拦截，等待用户重新输入
            else:
                logger.info(f"[{self.name}] 需求准入通过。")
                yield Event(
                    author="Senior_PM", 
                    # content={"parts": [{"text": "需求合法，已转交给需求专家为您服务。\n\n"}]},
                    actions=EventActions(state_delta={
                        "is_sanity_passed": True,
                        pm_output_key: pm_report
                    })
                )


        # --- [阶段二]：执行阶段 - 需求挖掘与用户确认 ---
        
        # A. 检查是否有审计反馈需要处理
        if audit_feedback:
            logger.info(f"[{self.name}] 检测到审计反馈，准备重新进入挖掘流程...")
            # 注意：实际重置操作在后面 yield 的 state_delta 中完成

        # B. 流程分支判断
        has_finished_mining = "[Discovery_Expert] 需求挖掘已完成" in discovery_output

        if not has_finished_mining:
            # 正常挖掘对话中
            async for event in self.discovery_actor.run_async(ctx):
                yield event
        elif not summary_shown:
            # 刚挖掘完，展示总结并引导用户确认
            logger.info(f"[{self.name}] 检测到挖掘完成标记，展示总结并引导用户确认...")
            summary_start = discovery_output.find("[Discovery_Expert] 需求挖掘已完成")
            summary_text = discovery_output[summary_start:]
            
            yield Event(
                author="Discovery_Phase_Manager",
                content={"parts": [{"text": f"{summary_text}\n\n---\n**请确认以上需求总结是否准确。如果确认无误，请回复“确认”或“继续”。如需修改，请直接说明需要调整的内容。**"}]},
                actions=EventActions(state_delta={
                    "summary_shown": True,
                    "audit_feedback": "" # 清除反馈标记
                })
            )
            return # 等待用户确认
        elif not user_confirmed:
            # 已展示总结，模型正在分析用户的最新回复是否为“确认”
            logger.info(f"[{self.name}] 正在分析用户确认意图...")
            async for event in self.discovery_actor.run_async(ctx):
                yield event
            
            # 检查最新的输出信号
            latest_output = ctx.session.state.get(output_key, "")
            if "[Discovery_Expert] 用户已确认" in latest_output:
                logger.info(f"[{self.name}] 检测到用户确认信号，进入审计流程。")
                yield Event(
                    author="Discovery_Phase_Manager",
                    content={"parts": [{"text": "收到确认，正在提交 CPO 进行最终审计..."}]},
                    actions=EventActions(state_delta={"user_confirmed": True})
                )
                # 不 return，继续向下执行阶段三（质量审计）
            elif "[Discovery_Expert] 用户要求修改" in latest_output:
                logger.info(f"[{self.name}] 检测到用户修改要求，重置流程。")
                yield Event(
                    author="Discovery_Phase_Manager",
                    content={"parts": [{"text": "好的，正在根据您的意见进行调整..."}]},
                    actions=EventActions(state_delta={"summary_shown": False})
                )
                return
            else:
                return # 继续等待用户明确意图
        
        # --- [阶段三]：职责 B - 质量审计 (仅在用户确认后触发) ---
        if user_confirmed:
            logger.info(f"[{self.name}] 触发 CPO 质量审计...")
            
            full_content = ""
            async for event in self.senior_pm.run_async(ctx):
                if event.content and event.content.parts:
                    part = event.content.parts[0]
                    if hasattr(part, "text") and part.text:
                        full_content += part.text
            
            pm_report = self._parse_json(full_content)
            
            if pm_report.get("verdict") == "REJECT":
                system_ins = pm_report.get("system_instructions", "请继续完善。")
                score = pm_report.get("score", 0)
                audit_feedback_text = f"CPO 审计未通过（得分 {score}）。反馈如下：\n{system_ins}"
                
                yield Event(
                    author="Senior_PM_Auditor", 
                    content={"parts": [{"text": f"审计未通过：{audit_feedback_text}"}]},
                    actions=EventActions(state_delta={
                        "user_confirmed": False, # 回到未确认状态
                        "summary_shown": False,   # 重新触发展示/总结逻辑
                        "audit_feedback": audit_feedback_text, # 将反馈注入 state
                        pm_output_key: pm_report
                    })
                )
                return
            else:
                score = pm_report.get("score", 0)
                if score >= 6:
                    yield Event(
                        author="Senior_PM_Auditor", 
                        content={"parts": [{"text": f"CPO 审计通过 (得分: {score})。正在申请文档归档..."}]},
                        actions=EventActions(state_delta={pm_output_key: pm_report})
                    )
                    
                    # --- [阶段四]：职责 C - 文档自动化归档 ---
                    ctx.session.state['doc_archive_request'] = f"请将以下经过审计的需求挖掘终产物归档为 'discovery_anchor'。内容如下：\n\n{discovery_output}"
                    
                    async for event in self.doc_auditor.run_async(ctx):
                        yield event
                    
                    return # 流程结束
                else:
                    yield Event(
                        author="Senior_PM_Auditor", 
                        content={"parts": [{"text": f"得分 {score}，请继续优化。"}]},
                        actions=EventActions(state_delta={pm_output_key: pm_report})
                    )

    def _parse_json(self, text: str) -> dict:
        """
        加固版 JSON 解析：
        1. 使用非贪婪匹配 r'\{.*?\}' 只抓取第一个对象
        2. 增加对嵌套结构的容错
        """
        import re
        import json
        try:
            # 使用非贪婪匹配 (.*?)，只抓取从第一个 { 到它最近的一个 }
            # 但如果 JSON 内部有嵌套的花括号，非贪婪匹配会提前截断。
            # 所以最佳实践是：匹配所有，然后手动处理。
            
            # 找到第一个 {
            start_idx = text.find('{')
            if start_idx == -1:
                return {}
            
            # 找到对应的最后一个 } (针对并排 JSON，我们尝试找到第一个完整闭合的块)
            # 这里使用一个简单的计数器来寻找第一个完整的 JSON 对象
            content = text[start_idx:]
            bracket_count = 0
            end_idx = 0
            for i, char in enumerate(content):
                if char == '{':
                    bracket_count += 1
                elif char == '}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx > 0:
                clean_json = content[:end_idx]
                return json.loads(clean_json)
            
            return {}
        except Exception as e:
            logger.error (f"JSON 解析极致加固失败: {e}")
            return {}
# 导出实例
discovery_phase_agent = DiscoveryPhaseAgent()