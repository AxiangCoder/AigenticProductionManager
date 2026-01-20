from google.adk.tools.tool_context import ToolContext
from e2b_code_interpreter import Sandbox
import os
from utils import logger

def python_executor(code: str, tool_context: ToolContext):
    """
    执行 Python 代码并返回运行结果、日志或错误信息。
    适用于需要进行复杂计算、数据处理、生成图表或验证逻辑的场景。

    Args:
        code: 需要在沙箱环境中执行的完整 Python 代码。
    """
    logger.info(f"Agent {tool_context.agent_name} 正在请求执行代码...")
    
    # E2B_API_KEY 需要在 .env 中配置
    api_key = os.getenv("E2B_API_KEY")
    
    try:
        # 使用 E2B 创建安全的沙箱环境
        with Sandbox(api_key=api_key) as sandbox:
            execution = sandbox.run_code(code)
            
            # 格式化输出结果
            return {
                "stdout": execution.logs.stdout,
                "stderr": execution.logs.stderr,
                "results": [str(r) for r in execution.results],
                "error": str(execution.error) if execution.error else None,
                "status": "success" if not execution.error else "failed"
            }
    except Exception as e:
        logger.error(f"代码执行异常: {str(e)}")
        return {
            "error": f"Internal Sandbox Error: {str(e)}",
            "status": "error"
        }