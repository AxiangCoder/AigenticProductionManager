import os
from google.adk.tools.tool_context import ToolContext
from utils import logger

def write_markdown_document(filename: str, content: str, tool_context: ToolContext):
    """
    创建或覆盖一个 Markdown (.md) 文档。

    Args:
        filename: 文件名（不含扩展名），例如 'PRD_v1'
        content: 完整的 Markdown 内容字符串
    """
    logger.info(f"[Tool Call] write_markdown_document: {filename} triggered by {tool_context.agent_name}")
    
    # 确保输出目录存在
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    file_path = os.path.join(output_dir, f"{filename}.md")
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "status": "success",
            "path": file_path,
            "message": f"文档 {filename}.md 已成功保存至 {output_dir}"
        }
    except Exception as e:
        logger.error(f"写入文档失败: {str(e)}")
        return {
            "status": "error",
            "message": f"写入失败: {str(e)}"
        }

def read_markdown_document(filename: str, tool_context: ToolContext):
    """
    读取已有的 Markdown 文档内容。

    Args:
        filename: 文件名（不含扩展名）
    """
    logger.info(f"[Tool Call] read_markdown_document: {filename} triggered by {tool_context.agent_name}")
    file_path = os.path.join("outputs", f"{filename}.md")
    
    if not os.path.exists(file_path):
        return {"status": "error", "message": "文件不存在"}
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_documents(tool_context: ToolContext):
    """
    列出当前 outputs 目录下的所有文档。
    """
    logger.info(f"[Tool Call] list_documents triggered by {tool_context.agent_name}")
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        return {"status": "success", "files": []}
        
    try:
        files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
        return {"status": "success", "files": files}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def delete_document(filename: str, tool_context: ToolContext):
    """
    删除指定的 Markdown 文档。

    Args:
        filename: 文件名（不含扩展名）
    """
    logger.info(f"[Tool Call] delete_document: {filename} triggered by {tool_context.agent_name}")
    file_path = os.path.join("outputs", f"{filename}.md")
    
    if not os.path.exists(file_path):
        return {"status": "error", "message": "文件不存在"}
        
    try:
        os.remove(file_path)
        return {"status": "success", "message": f"文档 {filename}.md 已删除"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
