# 用 Depends(函数名) 声明依赖，FastAPI 会在处理请求前先调用该函数，把返回值传给路由参数。

# 依赖注入 是把「获取某样东西」的逻辑单独写成函数，由 FastAPI 在每次请求时自动调用并传入路由。这样路由函数只关心业务逻辑，不必重复写「取参数、校验、获取数据库连接」等代码。

# 通俗理解：就像点外卖——你只说「我要一份盖浇饭」，平台自动帮你联系餐厅、安排骑手。你不需要自己打电话、自己取餐。Depends 就是 FastAPI 里的「自动安排」机制。


# 导入 FastAPI 和 Depends
from fastapi import FastAPI, Depends

# 创建应用
app = FastAPI()


# 第一层依赖：分页参数
def pagination(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}


# 第二层依赖：依赖 pagination，在其基础上增加 keyword
def search_params(pg: dict = Depends(pagination), keyword: str = None):
    return {**pg, "keyword": keyword or ""}


# 路由依赖 search_params（内部会先调用 pagination）
@app.get("/items")
def list_items(params: dict = Depends(search_params)):
    return params


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)