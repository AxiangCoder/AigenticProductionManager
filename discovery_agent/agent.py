from google.adk.agents.llm_agent import Agent
from utils import MODEL
from utils.load_prompt import load_prompt
from utils import AgentInfo

discovery_agent = Agent(
    model=MODEL,
    name=AgentInfo.DISCOVERY_AGENT['name'],
    description=AgentInfo.DISCOVERY_AGENT['description'],
    instruction=load_prompt(AgentInfo.DISCOVERY_AGENT['instruction_path']),
)

root_agent = discovery_agent
