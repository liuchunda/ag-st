import re
import threading
from tools.executor import execute_tool

# 定义一组代表“慢操作”的正则模式
_SLOW_PATTERNS = [
    r"pip\s+install",  # 匹配pip install命令
    r"npm\s+install",  # 匹配npm install命令
    r"npm\s+ci",  # 匹配npm ci命令
    r"yarn\s+install",  # 匹配yarn install命令
    r"docker\s+build",  # 匹配docker build命令
    r"cargo\s+build",  # 匹配cargo build命令
    r"go\s+build",  # 匹配go build命令
    r"python\s+-m\s+pytest",  # 匹配python -m pytest命令
    r"python\s+-m\s+build",  # 匹配python -m build命令
    r"\bpytest\b",  # 匹配pytest命令
    r"\bmake\b",  # 匹配make命令
    r"\bdeploy\b",  # 匹配deploy命令
    r"npm\s+run\s+build",  # 匹配npm run build命令
    r"npm\s+run\s+test",  # 匹配npm run test命令
]

# 后台任务计数器，默认为0
_bg_counter = 0
# 创建一个线程锁，用于保证对共享资源的操作是线程安全
background_lock = threading.Lock()
# 用于存储所有的后台任务，键为任务ID，值为任务信息字典
background_tasks = {}
# 存储后台任务的执行结果，键为任务ID，值为任务执行结果输出的内容
background_results = {}


def is_slow_operation(name, args):
    if name != "bash":
        return False
    # 获取bash命令
    cmd = args.get("command", "").lower()
    # 对所有的慢操作正则进行匹配，如果命令在任何一个慢操作正则匹配到了，则就是返回True
    return any(re.search(pattern, cmd) for pattern in _SLOW_PATTERNS)


# 判断操作是否要在后台运行
def should_run_background(name, args):
    if args.get("run_in_background", False):
        return True
    return is_slow_operation(name, args)


# 启动一个后台任务
def start_background_task(tool_call_id: str, name: str, args: dict):
    global _bg_counter
    _bg_counter += 1
    # 生成后台任务的ID
    bg_id = f"bg_{_bg_counter:04d}"
    # 获取要执行的后台命令
    cmd = args.get("command", name)

    def worker():
        try:
            result = execute_tool(name, args)
        except Exception as e:
            result = f"错误:{type(e).__name__}: {e}"
        # 对共享资源加锁，修改任务状态和记录任务执行结果
        with background_lock:
            background_results[bg_id] = result
            background_tasks[bg_id]["status"] = "completed"

    with background_lock:
        background_tasks[bg_id] = {
            "tool_call_id": tool_call_id,
            "command": cmd,
            "status": "running",
        }
    threading.Thread(target=worker, daemon=True).start()
    print(f"[后台]已经派发{bg_id}:{cmd[:40]}")
    return bg_id


def collect_background_results():
    with background_lock:
        # 先加锁，然后获取已经完成的后台任务的bg_id列表
        ready_ids = [
            bg_id
            for bg_id, task in background_tasks.items()
            if task["status"] == "completed"
        ]
    notifications = []
    for bg_id in ready_ids:
        with background_lock:
            task = background_tasks[bg_id]
            output = background_results.pop(bg_id, "")
        summary = output[:200] if len(output) > 200 else output
        notifications.append(
            f"<task_notification>\n"
            f"  <task_id>{bg_id}</task_id>"
            f"  <status>completed</status>"
            f"  <command>{task["command"]}</command>"
            f"  <summary>{summary}</summary>"
            f"</task_notification>\n"
        )
        print(f"[后台任务完成] {bg_id}: {task["command"]} ({len(output)}个字符)")
    return notifications
