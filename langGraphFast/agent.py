from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel
from pathlib import Path

from config.ai_configs import ai_configs
from config.env import env

cfg = ai_configs["bailian-qwen3.6-plus"]
# ChatOpenAI / init_chat_model 的 base_url 不需要 /chat/completions 后缀
base_url = cfg["url"].removesuffix("/chat/completions")
checkpointer = InMemorySaver()


class WeatherResponse(BaseModel):
    conditions: str


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"这里的天气一直很好 {city}!"


# 百炼是 OpenAI 兼容接口，需显式指定 model_provider="openai"
# qwen3.6-plus 默认 thinking 模式不支持 tool_choice=required，需关闭
model = init_chat_model(
    cfg["model"],
    model_provider="openai",
    api_key=env.llm_key_bailian.strip(),
    base_url=base_url,
    temperature=0,
    extra_body={"enable_thinking": False},
)

agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt="你是一个ai助手",
    # 百炼 thinking 模式不支持 provider 原生 structured output + tools，改用 ToolStrategy
    # response_format=ToolStrategy(WeatherResponse),
    checkpointer=checkpointer,
)
config = {"configurable": {"thread_id": "1"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "杭州天气如何"}]},
    config,
)
png_bytes = agent.get_graph().draw_mermaid_png()
out = Path(__file__).with_name("agent_graph.jpg")
out.write_bytes(png_bytes)
print(f"流程图已保存: {out}")
# print(response.get("structured_response"))
print(response["messages"][-1].content)
print(out,57)
