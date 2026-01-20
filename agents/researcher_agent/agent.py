from google.adk.agents.llm_agent import Agent
from utils import MODEL
from utils.load_prompt import load_prompt
from utils import AgentInfo

researcher_agent = Agent(
    model=MODEL,
    name=AgentInfo.RESEARCHER_AGENT['name'],
    description=AgentInfo.RESEARCHER_AGENT['description'],
    instruction=load_prompt(AgentInfo.RESEARCHER_AGENT['instruction_path']),
    output_key=AgentInfo.RESEARCHER_AGENT['output_key'],
)
