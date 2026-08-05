from pathlib import Path
from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from config.ai_configs import ai_configs
from config.env import env

cfg = ai_configs["bailian-qwen3.6-plus"]
# ChatOpenAI / init_chat_model 的 base_url 不需要 /chat/completions 后缀
base_url = cfg["url"].removesuffix("/chat/completions")
model = init_chat_model(
    cfg["model"],
    model_provider="openai",
    api_key=env.llm_key_bailian.strip(),
    base_url=base_url,
    temperature=0
)

class State(TypedDict):
    # messages 的类型是 list。注解里的 `add_messages` 定义了该状态字段如何更新
    # （这里是把新消息追加到列表，而不是覆盖原有内容）
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

def chatbot(state: State):
    return {"messages": [model.invoke(state["messages"])]}


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()


# 终端脚本里不用 IPython；把流程图保存为本地图片
try:
    png_bytes = graph.get_graph().draw_mermaid_png()
    out = Path(__file__).with_name("graph.png")
    out.write_bytes(png_bytes)
    print(f"流程图已保存: {out}")
except Exception as e:
    # 需要额外依赖（如绘制相关包），失败可忽略
    print(f"跳过绘图: {e}")