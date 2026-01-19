from typing import AsyncGenerator
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from .logger import logger

class SafeLiteLlm(LiteLlm):
    """
    LiteLlm 的安全封装，用于自动修复消息历史格式。
    它会在发送请求前合并连续的相同角色消息，以满足严格模型（如 Gemma/Llama）的 Chat Template 要求。
    """
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # 自动合并连续的相同角色消息
        if llm_request.contents:
            merged_contents = []
            for content in llm_request.contents:
                # logger.debug(f"llm_request.contents: {llm_request}")
                if not merged_contents:
                    merged_contents.append(content)
                else:
                    last_content = merged_contents[-1]
                    # 如果当前消息角色与上一条相同，则合并
                    if last_content.role == content.role:
                        if content.parts:
                            if last_content.parts is None:
                                last_content.parts = []
                            last_content.parts.extend(content.parts)
                    else:
                        merged_contents.append(content)
            llm_request.contents = merged_contents

        # 调用父类方法执行实际请求
        async for response in super().generate_content_async(llm_request, stream):
            yield response