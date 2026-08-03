import datetime

from langchain_core.tools import tool

@tool("get_nowtime", description="获取当前时间")
def get_nowtime():
  return f"现在时间是 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"