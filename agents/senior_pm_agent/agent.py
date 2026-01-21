from google.adk.agents import Agent # 注意：修复了导入路径
from utils import MODEL, AgentInfo
from utils.load_prompt import load_prompt
from tools import exif_loop
from google.adk.planners import PlanReActPlanner
from pydantic import BaseModel, Field
from typing import Literal

class AuditMetadata(BaseModel):
    """审计元数据"""
    current_stage: Literal["SanityCheck", "Auditor"] = Field(
        ..., 
        description="当前阶段：SanityCheck（需求准入验证）或 Auditor（执行者审计）"
    )
    target: str = Field(
        ..., 
        description="目标执行者名称，例如：Discovery_Expert、Architect_Expert"
    )
class SeniorPMOutput(BaseModel):
    """Senior PM Agent 的统一输出格式"""
    verdict: Literal["PASS", "REJECT"] = Field(
        ..., 
        description="评审结果：PASS（通过）或 REJECT（拒绝）"
    )
    score: float = Field(
        ..., 
        ge=0.0, 
        le=10.0, 
        description="评分：0.0-10.0 分，6.0 分及以上为通过"
    )
    human_message: str = Field(
        ..., 
        description="给用户的引导语。阶段一（准入验证）使用：温和的引导语；阶段二（审计通过）使用：'审计通过'"
    )
    system_instructions: str = Field(
        ..., 
        description="给执行者的处方级指令。阶段二使用：若是 REJECT，必须以 'COMMAND:' 开头，具体到哪一行、哪个逻辑节点需要修改"
    )
    audit_metadata: AuditMetadata = Field(
        ..., 
        description="审计元数据，包含当前阶段和目标执行者信息"
    )

def create_senior_pm_for(agent_config: dict):
    """
    最佳实践：为特定的执行者生成对应的 Senior PM 评审员
    """
    raw_instruction = load_prompt(AgentInfo.SENIOR_PM_AGENT['instruction_path'])
    
    # 动态填充提示词模板
    # 1. target_agent_name: 告诉 PM 它是谁的面试官
    # 2. content_to_audit: 将其设为 "{output_key}" 的形式
    #    这样 ADK 运行时会自动从全局 state[output_key] 中读取内容
    final_instruction = raw_instruction.replace(
        '{target_agent_name}', agent_config['name']
    ).replace(
        '{content_to_audit}', f"{{{agent_config['output_key']}}}"  # 双花括号表示保留占位符供运行时解析
    )
    
    return Agent(
        model=MODEL,
        name=f"Senior_PM_Auditor_for_{agent_config['name']}",
        instruction=final_instruction,
        output_key=AgentInfo.SENIOR_PM_AGENT['output_key'],
        output_schema=SeniorPMOutput,  # 使用 output_schema 约束输出格式
    )