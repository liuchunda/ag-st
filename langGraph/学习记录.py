from pydantic_settings import BaseSettings
from pydantic import Field

# BaseSettings这个是专门用来配置环境变量的，Field是制定必填或者默认值的 ...表示必填
# Field(...) 返回一个 FieldInfo 对象，挂在模型字段上，供 Pydantic 在校验/加载时读取。

class EnvSettings(BaseSettings):
  llm_key_local: str
  llm_key_local: str = Field(default="", env="LLM_KEY_LOCAL")
  llm_key_huoshan: str = Field(..., env="LLM_KEY_HUOSHAN")
  llm_key_bailian: str = Field(..., env="LLM_KEY_BAILIAN")

  class Config:
    env_file = ".env" //制定当前进程下的环境变量文件
    env_file_encoding = "utf-8"//制定当前进程下的环境变量文件的编码


env = EnvSettings()//实例化环境变量对象

# from app.config.env import env // 在别的文件中这样使用


# nput 是 Python 内置函数，不用 import，解释器自带。
# 作用：在终端打印提示（这里是带颜色的「请输入问题:」），然后阻塞等待你键盘输入，按回车后返回字符串。
if __name__ == "__main__":

  # 指定线程ID（会话ID），用于标识当前用户的对话。同一个thread_id表示同一个session
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
