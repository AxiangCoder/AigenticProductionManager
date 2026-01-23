import os
from typing import Optional
from .logger import logger


def load_document_by_path(document_path: str) -> Optional[str]:
    """
    根据文档路径加载文档内容
    
    Args:
        document_path: 文档路径（相对于项目根目录，如 "outputs/xxx.md"）
        
    Returns:
        文档内容，如果文档不存在则返回 None
    """
    if not document_path:
        return None
        
    # 确保路径是相对于项目根目录的
    if not os.path.exists(document_path):
        logger.warning(f"文档路径不存在: {document_path}")
        return None
    
    try:
        with open(document_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"已加载文档: {document_path}")
        return content
    except Exception as e:
        logger.error(f"读取文档失败: {e}")
        return None


def find_latest_document(
    output_dir: str = "outputs",
    keywords: Optional[list] = None,
    agent_name: str = ""
) -> Optional[str]:
    """
    从 outputs 目录查找最新的文档
    
    Args:
        output_dir: 输出目录路径，默认为 "outputs"
        keywords: 可选的关键词列表，用于过滤文件名（如 ["discovery", "PRD"]）
        agent_name: 智能体名称，用于日志输出
        
    Returns:
        文档内容，如果不存在则返回 None
    """
    if not os.path.exists(output_dir):
        logger.warning(f"[{agent_name}] {output_dir} 目录不存在")
        return None
    
    # 查找文档文件
    document_files = []
    try:
        for filename in os.listdir(output_dir):
            if filename.endswith(".md"):
                # 如果提供了关键词，检查文件名是否包含关键词
                if keywords:
                    if not any(keyword.lower() in filename.lower() for keyword in keywords):
                        continue
                
                file_path = os.path.join(output_dir, filename)
                # 按修改时间排序，最新的在前
                mtime = os.path.getmtime(file_path)
                document_files.append((mtime, file_path, filename))
    except Exception as e:
        logger.error(f"[{agent_name}] 读取 {output_dir} 目录失败: {e}")
        return None
    
    if not document_files:
        logger.warning(f"[{agent_name}] {output_dir} 目录下没有找到文档")
        return None
    
    # 按修改时间排序，取最新的
    document_files.sort(key=lambda x: x[0], reverse=True)
    latest_file = document_files[0][1]
    
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"[{agent_name}] 已加载文档: {document_files[0][2]}")
        return content
    except Exception as e:
        logger.error(f"[{agent_name}] 读取文档失败: {e}")
        return None
