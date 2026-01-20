from google.adk.agents.llm_agent import Agent
from utils import MODEL
from utils.load_prompt import load_prompt
from utils import AgentInfo

reviewer_agent = Agent(
    model=MODEL,
    name=AgentInfo.REVIEWER_AGENT['name'],
    description=AgentInfo.REVIEWER_AGENT['description'],
    instruction=load_prompt(AgentInfo.REVIEWER_AGENT['instruction_path']),
    output_key=AgentInfo.REVIEWER_AGENT['output_key']
)
