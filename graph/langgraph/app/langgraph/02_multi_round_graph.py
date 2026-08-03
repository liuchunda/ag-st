import uuid
from datetime import datetime
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from app.utils.generate_graph_png import generate_graph_png
from app.utils.llm_utils import create_llm
from app.utils.print_colors import Colors

if __name__ == '__main__':
  # 定义状态字典类，用于存储对话流程中的状态数据
  class State(TypedDict):
    # 用于存储标志信息的字符串字段
    flag: str
    # 用于存储消息列表，通过Annotated和add_messages确保消息能自动累加
    messages: Annotated[list, add_messages]


  # 创建内存中的检查点存储实例，用于保存和恢复对话状态
  checkpointer = InMemorySaver()
  # 初始化状态图构建器，指定使用State类作为状态类型
  graph_builder = StateGraph(State)

  # 调用自定义函数创建大语言模型实例
  llm = create_llm("bailian-qwen3.6-plus")


  # 定义聊天机器人节点的处理函数，接收当前状态并返回更新后的状态
  def llm_node(state: State):
    # 调用大语言模型处理当前消息列表，将生成的响应作为新消息添加到列表中
    return {"messages": [llm.invoke(state["messages"])]}


  # 向图中添加名为"llm_node"的节点，关联到chatbot处理函数
  graph_builder.add_node("llm_node", llm_node)
  # 添加从起始节点(START)到"llm_node"节点的边，定义流程起点
  graph_builder.add_edge(START, "llm_node")
  # 添加从"llm_node"节点到结束节点(END)的边，定义流程终点
  graph_builder.add_edge("llm_node", END)
  # 编译状态图，指定使用checkpoint作为检查点存储，实现状态持久化
  graph = graph_builder.compile(checkpointer=checkpointer)

  generate_graph_png(graph, "app/langgraph/02_multi_round_graph")


  # 定义流式处理图更新的函数，接收用户输入和配置信息
  def call_graph_stream(user_input: str, config: RunnableConfig):
    # 遍历图的stream方法返回的状态迭代器
    # 传入初始状态字典：flag设为"hello"，messages包含用户输入的消息
    # 传入配置参数config
    # 设置stream_mode为"values"，表示只返回状态值
    for state in graph.stream(
      {
        "flag": "hello",  # 一个state变量标识，用于标识graph.stream每次迭代的结果就是state
        "messages": [{"role": "user", "content": user_input}]  # 每次对话内容
      },
      config,
      stream_mode="values",
    ):
      # 打印当前消息列表的长度和完整状态信息
      print("/*---------------------------------------检测到流式更新-------------------------------------------*/")
      print(f"当前消息长度：{len(state['messages'])}")
      for index, msg in enumerate(state['messages']):
        print(index, msg.content)


  if __name__ == "__main__":

    # 指定线程ID（会话ID），用于标识当前用户的对话
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # 内层循环：处理当前用户的对话流程
    while True:
      # 提示用户输入问题
      user_input = input(f"{Colors.MAGENTA}请输入问题: {Colors.END}")
      # 检查用户是否输入退出指令
      if user_input.lower() in ["quit", "exit", "q"]:
        # 打印退回登录的提示信息
        print("退回登录。")
        # 跳出内层循环，回到登录界面
        break
      # 调用流式处理函数，传入用户输入和当前用户的配置
      call_graph_stream(user_input, config)