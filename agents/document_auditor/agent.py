from google.adk.agents import Agent
from utils import MODEL, AgentInfo
from utils.load_prompt import load_prompt
from tools.file_manager import write_markdown_document, read_markdown_document, list_documents, delete_document

def create_document_auditor():
    """
    工厂函数：创建文档审计员实例
    每次调用都会创建一个新的 Agent 实例，避免重复使用导致的父 agent 冲突
    """
    return Agent(
        model=MODEL,
        name=AgentInfo.DOCUMENT_AUDITOR_AGENT['name'],
        description=AgentInfo.DOCUMENT_AUDITOR_AGENT['description'],
        instruction=load_prompt(AgentInfo.DOCUMENT_AUDITOR_AGENT['instruction_path']),
        output_key=AgentInfo.DOCUMENT_AUDITOR_AGENT['output_key'],
        tools=[write_markdown_document, read_markdown_document, list_documents, delete_document]
    )
