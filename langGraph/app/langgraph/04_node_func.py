from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.utils.print_colors import print_yellow

if __name__ == "__main__":
  class State(TypedDict):
    input: str
    results: str


  def my_node(state: State, config: RunnableConfig):
    val = {"state": state, "config user_id": config.get('configurable').get('user_id')}
    print_yellow(f"my node: {val}")
    return {"results": f"Hello, {state['input']}!"}


  # 第二个参数config是可选的
  def my_other_node(state: State):
    print_yellow(f"my_other_node {state}", )
    return state


  builder = StateGraph(State)
  builder.add_node("my_node", my_node)
  builder.add_node("other_node", my_other_node)

  builder.add_edge(START, "my_node")
  builder.add_edge("my_node", "other_node")
  builder.add_edge("other_node", END)

  graph = builder.compile()
  print(
    "result", graph.invoke({"input": "hello world"}, {"configurable": {"user_id": "zhangsan"}})
  )