# 浏览器提交「字段 + 附件」时，Content-Type 多为 multipart/form-data（与纯 JSON 的 application/json 不同）。FastAPI 中：

# Form(...)：普通表单字段（字符串、数字等）。
# File(...)：可配合UploadFile表示上传文件；也可声明为bytes（整文件读入内存，只适合小文件）。
# UploadFile基于「临时文件/GC」流式读取，适合较大文件；用await file.read()按需读取，或用file.file 得到类文件对象

#   -H "Content-Type: multipart/form-data" \

# 导入 FastAPI、File、Form、UploadFile 模块
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

# 创建 FastAPI 应用对象
app = FastAPI()

# 定义 /submit 路由，POST 方法，接收表单字段 name 和可选文件 avatar
@app.post("/submit")
async def submit(
    # 接收表单提交的 name 字段（类型为 str）
    name: str = Form(),
    # 接收上传文件 avatar，可以为 None，类型为 UploadFile
    avatar: UploadFile | None = File(None)
):
    # 如果上传了头像文件，保存到当前目录
    if avatar and avatar.filename:
        save_path = Path(avatar.filename)
        content = await avatar.read()
        save_path.write_bytes(content)
        return {
            "name": name,
            "file": avatar.filename,
            "content_type": avatar.content_type,
            "saved_to": str(save_path.resolve()),
        }
    # 如果未上传头像，仅返回用户名和文件为 None
    return {"name": name, "file": None}

# 作为主程序运行时启动 Uvicorn 服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("7_3文件上传与表单:app", host="127.0.0.1", port=8000, reload=True)