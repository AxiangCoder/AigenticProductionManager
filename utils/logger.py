from loguru import logger
import sys

# 1. 立即移除默认的 handler（防止日志重复打印且格式不一）
logger.remove()

# 2. 添加你自定义的控制台 handler
# 这里可以自定义颜色、格式等
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"  # 设置为 DEBUG 以显示调试日志
)

# 3. 这里的 logger 已经是被配置过的实例了
# 你可以直接导出它
__all__ = ["logger"] 