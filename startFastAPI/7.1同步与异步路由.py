# 路由函数可以是普通的 def（同步），也可以是**async def**（异步）。

# 同步 def：在线程池中运行，适合 CPU 密集或大量同步 IO 的库（如部分数据库驱动）。
# 异步 async def：在事件循环中 await，适合 httpx.AsyncClient、aiosqlite 等高并发异步 IO 场景。
# 不要在 async def 路由里写长时间阻塞的同步代码（会卡住整个事件循环）；必要时仍用 def 交由线程池执行。

# 导入 FastAPI
from fastapi import FastAPI
from pydantic import BaseModel

# 创建应用
app = FastAPI()


class Item(BaseModel):
    name: str


# 同步路由：简单返回即可
@app.get("/sync")
def read_sync():
    return {"mode": "sync"}


# 异步路由：可在此 await 异步客户端、异步数据库等
@app.post("/async-demo", status_code=201)
async def create_async(item: Item):
    # 示例：这里没有 await，仅演示 async 路由与 201 状态码
    return {"created": True, "name": item.name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)