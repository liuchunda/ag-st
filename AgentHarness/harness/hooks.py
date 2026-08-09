from config import WORKDIR
import json

# 定义禁止执行的命令列表
DENY_LIST = [
    # rm -rf / 强制递归删除根目录 删除系统
    # sudo 以root权限执行
    # shutdown/reboot 关机/重启
    # mkfs 格式化磁盘
    # dd if= 用零覆盖磁盘 销毁所有的数据 不可恢复
    # > /dev/sda 重定向到块设备，会破坏分区表 会导致磁盘损坏
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "mkfs",
    "dd if=",
    "> /dev/sda",
]
# 定义需要用户确认或者审批的破坏性命令
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777", "del ", "erase "]

# 定义一个钩子字典，每个事件对应一个回调函数列表
HOOKS = {
    "UserPromptSubmit": [],  # 输入后、调用 LLM 前
    "PreToolUse": [],  # 收到 tool_call 后、执行 handler 前
    "PostToolUse": [],  # handler 执行后、下一轮前
    "Stop": [],  # 最终输出前
}


# 在工具调用前进行权限判断，如果不通过，返回不为None，如果通过返回None
def permission_hook(name: str, args: dict):
    print(
        f"\x1b[36m [HOOK] PreToolUse {name} {json.dumps(args,ensure_ascii=False)} \x1b[0m"
    )
    if name == "bash":
        for pattern in DENY_LIST:
            if pattern in args.get("command", ""):
                print(f"\n\x1b[31m⛔ 已拦截：'{pattern}'\x1b[0m")
                return "禁止列表拒绝权限"
        for kw in DESTRUCTIVE:
            if kw in args.get("command", ""):
                print(f"\n\x1b[33m⚠  可能破坏性的命令\x1b[0m")
                print(f"工具:{name}({args})")
                # 提示用户允许 执行输入y或yes才继续执行
                choice = input("是否允许执行?[y/N]").strip().lower()
                # 如果用户输入的不是y和yes
                if choice not in ("y", "yes"):
                    return "用户拒绝执行"
    if name in ("write_file", "edit_file"):
        # 获取要写入或编辑文件的路径
        path = args.get("path", "")
        # 如果检查到要写入的文件不在当前目录下
        if not (WORKDIR / path).resolve().is_relative_to(WORKDIR):
            print(f"\n\x1b[33m⚠  在工作区外面写入\x1b[0m")
            print(f"工具:{name}({args})")
            # 提示用户允许 执行输入y或yes才继续执行
            choice = input("是否允许执行?[y/N]").strip().lower()
            # 如果用户输入的不是y和yes
            if choice not in ("y", "yes"):
                return "用户拒绝执行"
    return None


# 这是打印工具调用信息的钩子
def log_hook(name: str, args: dict):
    print(
        f"\x1b[36m [HOOK] PreToolUse {name} {json.dumps(args,ensure_ascii=False)} \x1b[0m"
    )
    return None


def large_output_hook(name: str, args: dict, output):
    if len(str(output)) > 10000000:
        print(
            f"\n\x1b[33m[HOOK] PostToolUse ⚠  {name}输出结果过大:{len(str(output))}字符\x1b[0m"
        )


def summary_hook(messages: list):
    # 统计本次会话中工具调用的次数
    tool_count = sum(1 for m in messages if m.get("role") == "tool")
    print(f"\x1b[90m[HOOK] Stop: 本次会话共使用{tool_count}次工具调用\x1b[0m")
    return None


# 注册钩子函数，将回调函数添加到对应事件的钩子列表中
def register_hook(event: str, callback):
    HOOKS[event].append(callback)


# 触发用户输入相关的钩子链
def trigger_user_prompt_hooks(query: str) -> str:
    # 当前待处理的查询
    current = query
    # 依次触发钩子里的回调函数
    for callback in HOOKS["UserPromptSubmit"]:
        # 调用每个回调函数得到结果
        result = callback(current)
        if isinstance(result, str):
            current = result
    return current


# 通过钩子触发函数
def trigger_hooks(event: str, *args):
    # 按注册的顺序依次触发对应事件的钩子
    for callback in HOOKS[event]:
        # 调用钩子函数并获取返回值
        result = callback(*args)
        # 如果返回值不为None，则终止执行并返回result
        if result is not None:
            return result
    # 如果所有的钩子都正常返回None则表示通过最终返回None
    return None


def workspace_inject_hook(query: str) -> str | None:
    print(f"\x1b[90m[HOOK] UserPromptSubmit：注入工作目录 {WORKDIR}\x1b[0m")
    return f"<workspace>\n当前工作目录：{WORKDIR}\n</workspace>\n\n{query}"


# register_hook("UserPromptSubmit", workspace_inject_hook)
# register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)
