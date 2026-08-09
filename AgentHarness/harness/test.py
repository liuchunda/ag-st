# 说明：导入 asyncio
import asyncio

# 说明：导入 contextvars 模块
import contextvars

# 说明：创建一个名为 user 的上下文变量，默认值为 guest
user_var = contextvars.ContextVar("user", default="guest")


# 说明：定义处理请求的异步函数
async def handle_request(user):
    # 说明：在当前任务的上下文中设置用户名
    user_var.set(user)
    # 说明：模拟耗时 I/O
    await asyncio.sleep(0.1)
    # 说明：从当前上下文读取用户名（不会被其他任务覆盖）
    print(f"期望用户={user}, 实际读到={user_var.get()}")


# 说明：定义主协程
async def main():
    # 说明：并发处理两个请求
    await asyncio.gather(
        handle_request("alice"),
        handle_request("bob"),
    )


# 说明：运行主协程
asyncio.run(main())

handlers = {}
prefixed = "mcp__docs__search"

mcp_client = ""


def _make_handler(client, tname: str):
    def _handler(**kwargs):
        return client.call_tool(tname, kwargs)

    # return client.call_tool("search", "python")

    return _handler


# 为每一个工具调用生成一个单独的函数
handlers[prefixed] = _make_handler(mcp_client, "search")


# 这个代码是在动态创建函数(闭包) 用于将MCP工具调用封装成统一的处理函数
