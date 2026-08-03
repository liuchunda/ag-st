from langchain.agents import create_agent

from app.tools.agent_tools import agent_tools
from app.utils.llm_utils import create_llm
from app.utils.print_message import print_message, print_chunk_message


# 创建graph工作流
def create_graph():
  llm = create_llm("bailian-qwen3.6-plus")
  return create_agent(
    tools=agent_tools,
    model=llm,
    system_prompt="你是一名能够自主调用工具的智能助手"
  )


if __name__ == '__main__':

  print("/*---------------------------------------阻塞调用-------------------------------------------*/")
  _graph = create_graph()
  messages = _graph.invoke({"messages": [{"role": "user", "content": "今天上海天气如何"}]}).get("messages")

  for message in messages:
    print_message(message)

  print("\n\n/*---------------------------------------流式调用-------------------------------------------*/\n\n")

  for chunk in _graph.stream({"messages": [{"role": "user", "content": "今天南京天气如何"}]}):
    print_chunk_message(chunk)
