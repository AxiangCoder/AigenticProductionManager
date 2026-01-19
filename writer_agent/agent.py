from google.adk.agents.llm_agent import Agent
from utils import MODEL
from utils.load_prompt import load_prompt
from utils import AgentInfo

writer_agent = Agent(
    model=MODEL,
    name=AgentInfo.WRITER_AGENT['name'],
    description=AgentInfo.WRITER_AGENT['description'],
    instruction=load_prompt(AgentInfo.WRITER_AGENT['instruction_path']),
)
