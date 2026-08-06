# 当前端（如网页）从不同域名访问你的 API 时，浏览器会做跨域检查。若未配置 CORS，请求可能被拦截。

# 导入 FastAPI 类
from fastapi import FastAPI
# 导入用于支持跨域请求的 CORS 中间件
from fastapi.middleware.cors import CORSMiddleware

# 创建 FastAPI 应用实例
app = FastAPI()

# 配置并添加 CORS 中间件，允许所有来源的跨域请求
app.add_middleware(
    CORSMiddleware,
    # 允许所有来源访问，生产环境推荐填写具体域名
    allow_origins=["*"],
    # 允许客户端发送 cookies 等凭证信息
    allow_credentials=True,
    # 允许所有 HTTP 方法
    allow_methods=["*"],
    # 允许所有请求头
    allow_headers=["*"],
)

# 定义根路径的 GET 请求接口
@app.get("/")
def read_root():
    # 返回一条消息
    return {"message": "Hello"}

# 判断是否以脚本方式运行
if __name__ == "__main__":
    # 导入 uvicorn，用于运行 ASGI 服务器
    import uvicorn
    # 启动 FastAPI 应用，监听本地 127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)

