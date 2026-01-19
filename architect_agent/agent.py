from google.adk.agents.llm_agent import Agent
from utils import MODEL
from utils.load_prompt import load_prompt
from utils import AgentInfo

architect_agent = Agent(
    model=MODEL,
    name=AgentInfo.ARCHITECT_AGENT['name'],
    description=AgentInfo.ARCHITECT_AGENT['description'],
    instruction=load_prompt(AgentInfo.ARCHITECT_AGENT['instruction_path']),
)
