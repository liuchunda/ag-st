# 依赖注入常用于校验请求头、Token 等，通过后再把用户信息传给路由。从请求头读取参数需使用 Header。

# 导入 FastAPI、Depends、HTTPException、Security
from fastapi import FastAPI, Depends, HTTPException, Security
# 导入 APIKeyHeader
from fastapi.security import APIKeyHeader

# 创建应用
app = FastAPI()

# 定义从请求头 X-API-Key 读取 API Key 的规则
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# 依赖函数：校验 API Key，无效则抛出 403
def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != "secret-key-123":
        raise HTTPException(status_code=403, detail="无效的 API Key")
    return api_key


# 需要 API Key 的接口：依赖 verify_api_key
@app.get("/protected")
def read_protected(api_key: str = Depends(verify_api_key)):
    return {"message": "已通过校验", "key_prefix": api_key[:8] + "..."}


# 公开接口：不声明依赖
@app.get("/public")
def read_public():
    return {"message": "公开接口"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)