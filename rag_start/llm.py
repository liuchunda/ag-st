# 导入OpenAI客户端库
from openai import OpenAI
# 导入os库，用于读取环境变量
import os
# 导入logging库，用于记录日志
import logging
# 导入Optional类型，便于类型注解
from typing import Optional
from dotenv import load_dotenv
load_dotenv(override=True)
from utils.main import printLine

# 获取当前模块的logger日志对象
logger = logging.getLogger(__name__)

# 从环境变量获取OPENAI_BASE_URL，若未设置则使用默认地址
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
# 从环境变量获取 OPENAI_API_KEY（必须在 .env 中配置）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
printLine("OPENAI_API_KEY", "set" if OPENAI_API_KEY else "missing")
# 从环境变量获取模型名称，若未设置则使用默认模型名
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "doubao-seed-2-0-mini-260428")

# 全局OpenAI客户端实例，初始为None，延迟初始化
_client: Optional[OpenAI] = None

# 获取OpenAI客户端实例（单例模式）
def _get_client() -> OpenAI:
    """
    获取OpenAI客户端实例（单例模式）
    返回:
        OpenAI: 客户端实例
    """
    # 声明全局变量_client
    global _client
    # 如果客户端尚未初始化，则进行初始化
    if _client is None:
        # 如果API密钥不存在，则抛出异常
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY 未设置。请设置环境变量 OPENAI_API_KEY 或在代码中配置。"
            )
        # 使用指定的base_url和api_key初始化OpenAI客户端
        _client = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
        # 记录客户端初始化成功的日志
        logger.info(f"OpenAI客户端已初始化，base_url: {OPENAI_BASE_URL}")
    # 返回客户端实例
    return _client

# 定义调用大模型的函数
def invoke(prompt: str, model: Optional[str] = None, temperature: float = 0.7) -> str:
    """
    调用大模型生成回复

    参数:
        prompt (str): 输入的提示词
        model (str, optional): 模型名称，默认使用环境变量或默认值
        temperature (float): 生成温度，默认0.7

    返回:
        str: 大模型生成的回复内容

    异常:
        ValueError: API密钥未设置
        Exception: API调用失败
    """
    try:
        # 获取OpenAI客户端对象
        client = _get_client()
        # 如果model参数为空，则使用默认模型名
        model_name = model or MODEL_NAME

        # 记录调试日志，显示模型名和prompt长度
        logger.debug(f"调用大模型，model: {model_name}, prompt长度: {len(prompt)}")

        # 调用OpenAI聊天模型接口生成回复
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            temperature=temperature,
        )

        # 获取大模型生成的回复内容
        content = response.choices[0].message.content
        # 记录调试日志，标记回复内容的长度
        logger.debug(f"大模型回复生成成功，长度: {len(content) if content else 0}")
        # 返回回复内容（若为空则返回空字符串）
        return content or ""

    # 捕捉并处理ValueError异常（如API密钥未配置）
    except ValueError as e:
        logger.error(f"配置错误: {str(e)}")
        raise
    # 捕捉并处理所有其他异常
    except Exception as e:
        logger.error(f"调用大模型失败: {str(e)}")
        raise