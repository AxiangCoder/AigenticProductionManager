"""
JSON 解析工具函数
提供加固版的 JSON 解析功能，能够从包含其他文本的字符串中提取 JSON 对象
"""
import json
from utils import logger


def parse_json(text: str) -> dict:
    """
    加固版 JSON 解析：
    1. 从包含其他文本的字符串中提取第一个完整的 JSON 对象
    2. 支持嵌套结构的容错处理
    3. 使用括号计数找到第一个完整闭合的 JSON 对象
    
    Args:
        text: 可能包含 JSON 对象的文本字符串
        
    Returns:
        解析后的字典，如果解析失败则返回空字典 {}
    """
    try:
        # 找到第一个 {
        start_idx = text.find("{")
        if start_idx == -1:
            return {}

        # 找到对应的最后一个 } (针对并排 JSON，我们尝试找到第一个完整闭合的块)
        # 这里使用一个简单的计数器来寻找第一个完整的 JSON 对象
        content = text[start_idx:]
        bracket_count = 0
        end_idx = 0
        for i, char in enumerate(content):
            if char == "{":
                bracket_count += 1
            elif char == "}":
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break

        if end_idx > 0:
            clean_json = content[:end_idx]
            return json.loads(clean_json)

        return {}
    except Exception as e:
        logger.error(f"JSON 解析失败: {e}")
        return {}
