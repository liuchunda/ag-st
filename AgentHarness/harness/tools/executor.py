import inspect
import json
from tools.handlers import TOOL_HANDLERS
from config import client, MODEL_ID, DEFAULT_MAX_TOKENS
from prompt import SUB_SYSTEM
from hooks import trigger_hooks
from tools.schema import BASE_TOOLS
from utils import assistant_message_dict, extract_text


# 接收工具名称和参数字典，返回结果args={"name":"zhangsan","age":18,"command":'dir'}
def execute_tool(name: str, args: dict, handlers=None) -> str:
    pool = handlers if handlers is not None else TOOL_HANDLERS
    # 根据工具名称从TOOL_HANDLERS获取对应的处理函数
    handler = pool.get(name)
    # 如果没有找到处理函数，则返回错误提示
    if not handler:
        return f"未知工具: {name}"
    # 获取处理函数的参数签名
    sig = inspect.signature(handler)
    # 含**kwargs时透传全部参数(MCP工具等动态schema),判断是否存在**kwargs可变关键字参数
    has_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if has_var_kw:
        return str(handler(**args))
    # 从输入参数中筛选出处理函数所需要的有效参数
    valid = {k: v for k, v in args.items() if k in sig.parameters}
    return handler(**valid)


# 定义运行子Agent的函数，参数为描述字符串，返回字符串
def run_spawn_subagent(description: str):
    print("\x1b[35m [子Agent已启动]  \x1b[0m")
    # 创建一个新的上下文列表 用户的描述为第一条用户消息
    messages = [{"role": "user", "content": description}]
    # 最多进行30轮的消息交互
    for _ in range(30):
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "system", "content": SUB_SYSTEM}, *messages],  # type: ignore
            tools=BASE_TOOLS,  # type: ignore
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        assistant = response.choices[0].message
        messages.append(assistant_message_dict(assistant))
        if not assistant.tool_calls:
            break
        for tool_call in assistant.tool_calls:
            name = tool_call.function.name  # type: ignore
            args = json.loads(tool_call.function.arguments or "{}")  # type: ignore
            blocked = trigger_hooks("PreToolUse", name, args)
            # 如果被拒绝了，则加入一个tool的回复，内容为阻止的理由
            if blocked:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(blocked),
                    }
                )
                continue
            # 执行工具，如果此工具未注册，则提示未知工具
            output = (
                execute_tool(name, args)
                if name in TOOL_HANDLERS
                else f"未知工具:{name}"
            )
            trigger_hooks("PostToolUse", name, args, output)
            print(f"\x1b[90m [SubAgent] {name}: {str(output)[:100]}  \x1b[0m")
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": output}
            )
    # 从所有的消息中最后一条内容中提取文本为最终的结果
    result = extract_text(messages[-1].get("content"))
    # 如果没有提取到，反向查找assistant角色消息并提取结果
    if not result:
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                result = extract_text(msg.get("content"))
                if result:
                    break
    print(f"\x1b[35m [SubAgent]完成任务  \x1b[0m")
    return result


TOOL_HANDLERS["spawn_subagent"] = run_spawn_subagent
