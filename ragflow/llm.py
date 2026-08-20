import logging
logger = logging.getLogger(__name__)
from openai import OpenAI
SYSTEM_PROMPT = """
你是知识库助手，请严格根据[检索到的参考资料]回答用户的问题
回答要求：
1. 仅依赖参考资料作答： 资料不足时请明确说明[根据现有的知识库无法确定]，不要编造
2. 关键结论尽量引用资料来源(如文本名)，便于业务同事核对
3. 表述专业、简洁，适合企业内部的沟通
4. 若资料之间存在冲突，请指出差异并说明依据
"""

class LLMClient:
    def __init__(self,config:dict):
        self.config = config
        self._client = None
    
    def _get_client(self)->OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
            )
        return self._client
    
    def generate_response(self,user_prompt:str)->str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content= response.choices[0].message.content or ""
        logger.info(f"LLM生成响应: {content}")
        return content