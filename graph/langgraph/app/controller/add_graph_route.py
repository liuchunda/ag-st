from fastapi import FastAPI
from langserve import add_routes

from app.langgraph.agent import create_graph
from app.langgraph._01_simple_graph import create_graph as create_graph_01


# 注册路由
def add_graph_route(app: FastAPI):
  add_routes(
    app=app,
    runnable=create_graph(),
    path="/agent",
  )
  add_routes(
    app=app,
    runnable=create_graph_01(),
    path="/agent_01",
  )
