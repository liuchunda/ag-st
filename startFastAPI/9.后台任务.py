# BackgroundTasks 用于在响应返回之后执行一些耗时或非关键操作，如发邮件、写日志、清理缓存。客户端不用等这些任务完成，就能先收到响应。

# 通俗理解：就像餐厅——顾客点完餐，服务员先回复「好的，马上做」，然后去后厨下单。顾客不用站在柜台等菜做好。BackgroundTasks 就是「先回复，再在后台慢慢做」的机制。

# 导入 FastAPI Web 框架和后台任务模块
from fastapi import FastAPI, BackgroundTasks

# 创建一个 FastAPI 应用实例
app = FastAPI()

# 定义一个模拟发送邮件的后台任务函数
def send_email(email: str, content: str):
    # 打印后台邮件发送信息
    print(f"[后台] 发送邮件给 {email}: {content}")

# 定义 /notify 路由，POST 请求
@app.post("/notify")
# 路由处理函数，接收 email 参数和后台任务对象
def notify_user(email: str, background_tasks: BackgroundTasks):
    # 添加 send_email 任务到后台，响应先返回后再执行任务
    background_tasks.add_task(send_email, email, "您有一条新通知")
    # 立即返回响应内容（不等待邮件发送完成）
    return {"message": "通知已提交"}

# 仅当本文件作为主程序运行时才执行以下代码
if __name__ == "__main__":
    # 导入 uvicorn 服务器
    import uvicorn
    # 启动 FastAPI 应用，监听127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)