from langchain.chat_models import init_chat_model

from app.config.ai_configs import ai_configs


def create_llm(
  platform_code='huoshan-doubao',
  temperature=0.5,
  disable_streaming=False,
):
  _ai_config = ai_configs.get(platform_code)

  if _ai_config is None:
    raise Exception('Unknown platform code', platform_code)

  return init_chat_model(
    # 必须填 openai（兼容协议）
    model_provider="openai",
    # 你的模型名
    model=_ai_config.get('model'),
    # 你的自定义 API URL
    base_url=_ai_config.get('url').replace("chat/completions", ""),
    # 本地模型随便填
    api_key=_ai_config.get('key'),
    # 随机性
    temperature=temperature,
    # 禁用流式响应
    disable_streaming=disable_streaming,
    extra_body={
      # qwen模型禁用思考
      "enable_thinking": False,
    }
  )

if __name__ == '__main__':
  model = create_llm()
  print(model.invoke("你好，你是谁").content)