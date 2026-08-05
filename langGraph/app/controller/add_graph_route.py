from fastapi import FastAPI
from langserve import add_routes

from app.langgraph.agent import create_graph


# 注册路由
def add_graph_route(app: FastAPI):
  add_routes(
    app=app,
    runnable=create_graph(),
    path="/agent",
  )