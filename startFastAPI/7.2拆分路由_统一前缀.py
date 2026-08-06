# 项目变大时，可用 APIRouter把不同模块的路由分开，再用include_router挂到主应用上，并设置prefix、tags（文档里分组显示）。

# 导入 FastAPI 与 APIRouter
from fastapi import FastAPI, APIRouter

# 主应用
app = FastAPI()

# 用户模块路由：前缀 /users，文档标签「用户」
user_router = APIRouter(prefix="/users", tags=["用户"])


@user_router.get("/")
def list_users():
    return [{"id": 1, "name": "张三"}]


@user_router.get("/{user_id}")
def get_user(user_id: int):
    return {"id": user_id, "name": "示例"}


# 挂载到主应用
app.include_router(user_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)