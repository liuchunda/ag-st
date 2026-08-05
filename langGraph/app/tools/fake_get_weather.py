from typing import Annotated

from langchain_core.tools import tool


# 查询天气工具
@tool("get_weather", description="获取天气信息")
def fake_get_weather(
  city: Annotated[str, '查询天气的城市名称'],
  date: Annotated[str, '查询天气的日期，格式为 YYYY-MM-DD']
):
  return f"时间 {date}， {city} 天气局部有阵雨，温度 10 度，风向 东南。"