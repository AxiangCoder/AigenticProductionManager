from google.adk.agents import LlmAgent

from agents.senior_pm_agent import create_senior_pm_for
from agents.document_auditor import create_document_auditor
from utils.load_prompt import load_prompt
from utils import MODEL, AgentInfo
from tools.file_manager import write_markdown_document, read_markdown_document, list_documents, delete_document
from google.genai import types



# 创建所有子智能体
discovery_agent = LlmAgent(
    model=MODEL,
    name=AgentInfo.DISCOVERY_AGENT['name'],
    instruction=load_prompt(AgentInfo.DISCOVERY_AGENT['instruction_path']),
    output_key=AgentInfo.DISCOVERY_AGENT['output_key'],
    generate_content_config=types.GenerateContentConfig(
        temperature=1, # 更确定性的输出
    )
)

researcher_agent = LlmAgent(
    model=MODEL,
    name=AgentInfo.RESEARCHER_AGENT['name'],
    instruction=load_prompt(AgentInfo.RESEARCHER_AGENT['instruction_path']),
    output_key=AgentInfo.RESEARCHER_AGENT['output_key'],
)

architect_agent = LlmAgent(
    model=MODEL,
    name=AgentInfo.ARCHITECT_AGENT['name'],
    instruction=load_prompt(AgentInfo.ARCHITECT_AGENT['instruction_path']),
    output_key=AgentInfo.ARCHITECT_AGENT['output_key'],
)

reviewer_agent = LlmAgent(
    model=MODEL,
    name=AgentInfo.REVIEWER_AGENT['name'],
    instruction=load_prompt(AgentInfo.REVIEWER_AGENT['instruction_path']),
    output_key=AgentInfo.REVIEWER_AGENT['output_key'],
)

writer_agent = LlmAgent(
    model=MODEL,
    name=AgentInfo.WRITER_AGENT['name'],
    instruction=load_prompt(AgentInfo.WRITER_AGENT['instruction_path']),
    output_key=AgentInfo.WRITER_AGENT['output_key'],
)

document_auditor = create_document_auditor()

# 创建针对不同阶段的 PM 审计员
senior_pm_discovery = create_senior_pm_for(AgentInfo.DISCOVERY_AGENT)
senior_pm_architect = create_senior_pm_for(AgentInfo.ARCHITECT_AGENT)
senior_pm_writer = create_senior_pm_for(AgentInfo.WRITER_AGENT)

# 创建 agentic_pm 智能体
agentic_pm = LlmAgent(
    model=MODEL,
    name="Agentic_PM",
    description="高度智能化的产品经理智能体，具备自主规划、工具使用和子智能体协调的能力",
    instruction=load_prompt("agents/agentic_pm/agentic_pm.md"),
    generate_content_config=types.GenerateContentConfig(
        temperature=0, # 更确定性的输出
    ),
    sub_agents=[
        discovery_agent,
        researcher_agent,
        architect_agent,
        reviewer_agent,
        writer_agent,
        document_auditor,
        senior_pm_discovery,
        senior_pm_architect,
        senior_pm_writer,
    ],
    tools=[
        write_markdown_document,
        read_markdown_document,
        list_documents,
        delete_document,
    ],
)
