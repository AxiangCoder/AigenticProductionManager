from google.adk.agents import Agent # 注意：修复了导入路径
from utils import MODEL, AgentInfo
from utils.load_prompt import load_prompt
from tools import exif_loop

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
        # tools=[exif_loop] # 必须挂载退出工具
    )