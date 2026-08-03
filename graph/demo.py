from langgraph.graph import StateGraph, MessagesState, START, END
# from langgraph.graph.message import message_to_dict
import json
# from app.utils.llm_utils import create_llm
def mock_llm(state: MessagesState):
  return {"messages": [{"role": "ai", "content": "你好 世界"}]}

builder = StateGraph(MessagesState)
builder.add_node(mock_llm)
builder.add_edge(START, "mock_llm")
builder.add_edge("mock_llm", END)
graph = builder.compile()
# print(dir(graph),11)
# print(
#   "执行结果",
#   graph.invoke({"messages": [{"role": "user", "content": "嗨!"}]})
# )
result = graph.invoke({"messages": [{"role": "user", "content": "嗨!"}]})
# print(json.dumps({"name":"你好","age":12},ensure_ascii=False, indent=2))
# j = json.dumps({"name":"你好","age":12},ensure_ascii=False, indent=2)
messages = [m.model_dump() for m in result["messages"]]
print(json.dumps(messages,ensure_ascii=False, indent=2))

