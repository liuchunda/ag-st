from langchain.agents import AgentState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AIMessageChunk, ToolMessage


def print_message(message: HumanMessage | AIMessage | SystemMessage | ToolMessage):
  if isinstance(message, dict):
    print(message)
    return

  if message.type == "human":
    print('\n🧑‍💬 人类消息:\n\n', message.content)
  elif message.type == "ai":
    if len(message.tool_calls):
      print('\n🔧 大模型工具调用:\n\n', message.tool_calls)
    else:
      print('\n✨ 大模型消息:\n\n', message.content)
  elif message.type == "system":
    print('\n◈ 系统提示词:\n\n', message.content)
  elif message.type == "tool":
    print('\n📋 工具调用结果:\n\n', message.content)


def print_chunk_message(chunk_state: dict):
  if 'model' in chunk_state:
    # 获取代理返回的消息列表中的第一条消息
    chunk_message = chunk_state.get('model').get('messages')[0]
    # 若消息包含工具调用信息，打印工具调用详情
    if len(chunk_message.tool_calls):
      print('\n🔧 大模型工具调用::\n\n', chunk_message.tool_calls)
    # 否则打印代理的直接输出内容
    else:
      print('\n✨ 大模型消息:\n\n', chunk_message.content)
  # 若 chunk 包含工具（tools）的执行结果
  elif 'tools' in chunk_state:
    print('\n🛠️ 工具执行：', chunk_state)
    # 打印工具返回的消息内容
    print('\n🛠️ 工具输出:', chunk_state.get('tools').get('messages')[0].content)
  # 其他类型的消息
  else:
    print('\n其他消息:', chunk_state)