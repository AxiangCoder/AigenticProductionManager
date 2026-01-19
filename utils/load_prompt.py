from pathlib import Path

def load_prompt(prompt_file: str) -> str:
    """
    加载 prompt 文件内容
    
    Args:
        prompt_file: 相对于项目根目录的文件路径，例如 "agents/architect_agent/architect.md"
    
    Returns:
        prompt 文件的文本内容
    
    Raises:
        FileNotFoundError: 如果文件不存在
    """
    # 获取项目根目录（utils 目录的父目录）
    project_root = Path(__file__).parent.parent
    # 构建完整路径
    full_path = project_root / prompt_file
    
    # 检查文件是否存在
    if not full_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {full_path}")
    
    with open(full_path, 'r', encoding='utf-8') as file:
        return file.read()