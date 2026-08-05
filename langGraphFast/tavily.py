from langchain_tavily import TavilySearch
from config.env import env
tool = TavilySearch(
    max_results=2,
    tavily_api_key=env.tavily_api_key.strip(),
)
tools = [tool]
tool.invoke("What's a 'node' in LangGraph?")