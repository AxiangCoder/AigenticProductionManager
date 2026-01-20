from google.adk.tools.tool_context import ToolContext

from utils import logger


def exif_loop (tool_context: ToolContext):
  logger.info(f"[Tool Call] exif_loop_tool triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  return {}