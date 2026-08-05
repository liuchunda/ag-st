from typing import Literal

from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END

from app.tools.agent_tools import agent_tools
from app.utils.generate_graph_png import generate_graph_png
from app.utils.llm_utils import create_llm
from app.utils.print_message import print_message

if __name__ == '__main__':
  # 模型对象
  llm_with_tools = create_llm().bind_tools(agent_tools)

  # 根据工具名称获取工具对象
  tools_by_name = {tool.name: tool for tool in agent_tools}


  # 大模型节点
  def model_node(state: MessagesState):
    return {
      "messages": [
        # 将用户的最新消息以及历史消息发送给大模型
        # 将大模型返回的 AiMessage 放到数组中，也就是用 {"messages":[AiMessage]} 这个字典更新图的状态
        llm_with_tools.invoke(
          [SystemMessage(content="你是一个能够自主决策进行工具调用的智能助手")]
          + state["messages"]
        )
      ]
    }


  # 工具执行节点
  def tool_node(state: MessagesState):
    """Performs the tool call"""

    result = []
    # 取出来最后一条消息的 tool_calls数组，按照这个工具调用消息执行工具
    for tool_call in state["messages"][-1].tool_calls:
      tool = tools_by_name[tool_call["name"]]
      observation = tool.invoke(tool_call["args"])
      # 将结果包装成工具消息ToolMessage，放到结果数组results中；
      result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))

    # 将工具节点的执行结果，用 {"messages":[ToolMessage,ToolMessage,...]} 这个字典更新图状态
    return {"messages": result}


  # model_node到tool_node的边判断是否继续执行工具
  def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    messages = state["messages"]
    last_message = messages[-1]

    # 如果最后一条消息是工具调用，则流转到工具执行节点
    if last_message.tool_calls:
      return "tool_node"

    # 否则最后一条消息就是大模型的回复消息，直接结束
    return END


  # 定义画布
  graph_builder = StateGraph(MessagesState)

  # 给画布添加节点
  graph_builder.add_node("model_node", model_node)
  graph_builder.add_node("tool_node", tool_node)

  # 给画布添加边
  graph_builder.add_edge(START, "model_node")
  graph_builder.add_conditional_edges("model_node", should_continue, ["tool_node", END])
  graph_builder.add_edge("tool_node", "model_node")

  # 将画布编译为工作流
  graph = graph_builder.compile()

  # 绘制画布
  generate_graph_png(graph, "app/langgraph/01_simple_graph")

  # 执行工作流
  messages = [HumanMessage(content="今天上海天气咋样")]
  messages = graph.invoke({"messages": messages})
  for msg in messages["messages"]:
    print_message(msg)
