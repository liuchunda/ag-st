# 导入 FastAPI 类
from fastapi import FastAPI, Query
from typing import Optional
# 导入 uvicorn 用于启动服务器
import uvicorn
# 创建 FastAPI 应用实例，title 会显示在自动文档中
app = FastAPI(title="我的第一个 API")

# 使用 @app.get 定义 GET 请求的路由，"/" 表示根路径
@app.get("/")
def read_root():
    # 返回一个字典，FastAPI 会自动转为 JSON
    return {"message": "Hello, FastAPI!"}


# 定义 GET /items/{item_id}，item_id 是路径参数
# @app.get("/items/{item_id}")
# def read_item(item_id: int):
#     # 路径参数会自动解析并做类型校验
#     return {"item_id": item_id, "name": f"商品{item_id}"}

# 定义 GET /items，skip/limit 是查询参数（?skip=0&limit=10）
@app.get("/items")
def read_item_list(skip: int = 0, limit: int = 10):
    # 函数参数默认就是 query 参数，会自动解析并做类型校验
    return {"skip": skip, "limit": limit}


# 导入 FastAPI、Query 与 Optional 类型


# q 可选；skip 有默认值且必须 >= 0；limit 默认 10 且范围 1~100

# 参数	全称	含义
# ge
# greater than or equal
# ≥ 大于等于
# le
# less than or equal
# ≤ 小于等于
@app.get("/search")
def search(
    q: Optional[str] = Query(None, max_length=50, description="关键词"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    
):
    return {"q": q, "skip": skip, "limit": limit}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)




# 程序入口：直接运行此文件时执行
if __name__ == "__main__":

    # 启动服务器，host 和 port 为监听地址和端口
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)