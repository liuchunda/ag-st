import os
import subprocess
from utils import decode_subprocess_output, safe_path
from config import TEXT_ENCODING, WORKDIR, TEAMMATE_WAIT_TIMEOUT
import glob as g
from skills import run_load_skill
from tasks import (
    create_task,
    list_tasks,
    get_task,
    claim_task,
    complete_task,
    delete_task,
)
import json
from dataclasses import asdict
from cron import schedule_cron, cancel_cron, scheduled_jobs, cron_lock
from teams import (
    spawn_teammate_thread,
    BUS,
    LEAD_NAME,
    is_teammate_running,
    current_agent,
    consume_inbox,
    format_inbox_messages,
    run_request_shutdown,
    run_request_plan,
    run_submit_plan,
    run_review_plan,
    wait_for_teammates,
)
from worktrees import run_create_worktree, run_remove_worktree, run_keep_worktree
from pathlib import Path
from mcp import run_connect_mcp


def run_bash(
    command: str, run_in_background: bool = False, cwd: Path | None = None
) -> str:
    # 定义一些危险的命令列表
    dangerous = ["rm -rf", "sudo", "shutdown", "reboot", "> /dev/"]
    # 如果要执行的命令中包含任何一个危险命令，
    if any(d in command for d in dangerous):
        # 则返回错误提示，拦截拒绝执行危险命令
        return "错误:危险命令已经被拦截"
    try:
        # 得到的stdout和stderr是二进制的字节序列
        result = subprocess.run(
            command,  # 要执行的命令
            shell=True,  # 在shell中执行
            cwd=str(cwd) if cwd else os.getcwd(),  # 把当前的工作目录设置为当前的路径
            capture_output=True,  # 捕获标准输出和标准错误输出
            timeout=120,  # 超时时间设置为120秒
        )
        out = decode_subprocess_output(
            (result.stdout or b"") + (result.stderr or b"")
        ).strip()
        return out[:500000] if out else "(无输出)"
    except subprocess.TimeoutExpired:
        return "错误： 超时(120秒)"
    except (FileNotFoundError, OSError) as e:
        return f"错误:{str(e)}"


def run_read(path: str, limit: int | None = None, cwd: Path | None = None) -> str:
    try:
        # 使用safe_path校验并获取文件的路径，并指定编码读取内容并按行分割
        lines = safe_path(path, cwd).read_text(encoding=TEXT_ENCODING).splitlines()
        # 如果有行数限制，并且限制小于真实的行数
        if limit and limit < len(lines):
            # 截取前limit行，并在最后添加提示剩余行数的说明
            lines = lines[:limit] + [f"...(还有{len(lines)-limit}行)"]
        return "\n".join(lines)
    except Exception as e:
        return f"错误: {str(e)}"


def run_write(path: str, content: str, cwd: Path | None = None) -> str:
    try:
        # 获取文件安全路径
        file_path = safe_path(path, cwd)
        # 确保父目录是存在的，不存在则创建
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # 指定的编码写入指定内容到指定文件
        file_path.write_text(content, encoding=TEXT_ENCODING)
        return f"已经写入{len(content)}字节到{path}中"
    except Exception as e:
        return f"错误: {str(e)}"


def run_edit(path: str, old_text: str, new_text: str, cwd: Path | None = None) -> str:
    try:
        # 获取文件安全路径
        file_path = safe_path(path, cwd)
        # 读取文件的内容
        text = file_path.read_text()
        if old_text not in text:
            return f"错误：在{path}没有找到指定的文本{old_text}"
        file_path.write_text(
            text.replace(old_text, new_text, 1), encoding=TEXT_ENCODING
        )
        return f"已经编辑{path}"
    except Exception as e:
        return f"错误: {str(e)}"


def run_glob(pattern: str, cwd: Path | None = None) -> str:
    try:
        results = []
        root = cwd if cwd is not None else WORKDIR
        # 遍历所有的匹配到的路径，根目录为WORKDIR
        for match in g.glob(pattern, root_dir=root):
            # 检查匹配到的路径是否是相对于WORKDIR的子路径
            if (root / match).resolve().is_relative_to(root):
                results.append(match)
        return "\n".join(results) if results else "(无匹配)"

    except Exception as e:
        return f"错误:{e}"


# 全局变量CURRENT_TODOS，用于存储当前的任务列表，类型为list[dict]
CURRENT_TODOS: list[dict] = []


def todo_update_reminder(rounds_since: int, threshold: int):
    # 如果当前的轮数小于阈值或者当前 任务为空
    if rounds_since < threshold or not CURRENT_TODOS:
        return None
    # 找出尚未完成的TODO
    active = [
        todo
        for todo in CURRENT_TODOS
        if todo.get("status") in ("pending", "in_progress")
    ]
    # 如果没有尚未完成的TODO
    if not active:
        return None
    lines = [
        f"[TODO提醒] 有未完成的任务，且连续{rounds_since}轮未调用todo_write,请更新进度",
        "当前的任务:",
    ]
    for todo in CURRENT_TODOS:
        lines.append(f"- [{todo.get('status','?')}] {todo.get('content','')}")
    return "\n".join("lines")


# 定义更新CURRENT_TODOS的函数，接收新的todos，返回字符串
def run_todo_write(todos: list) -> str:
    global CURRENT_TODOS
    for index, todo in enumerate(todos):
        if "content" not in todo or "status" not in todo:
            return f"错误: todos[{index}] 缺少content或status字段"
        if todo["status"] not in ("pending", "in_progress", "completed"):
            return f"错误: todos[{index}] 状态无效"
    CURRENT_TODOS = todos
    lines = ["\x1b[33m ## 当前任务 \x1b[0m"]
    for todo in CURRENT_TODOS:
        icon = {
            "pending": "\x1b[33m等待中\x1b[0m",
            "in_progress": "\x1b[33m处理中\x1b[0m",
            "completed": "\x1b[33m已完成\x1b[0m",
        }[todo["status"]]
        lines.append(f"- [{icon}] {todo['content']}")
    print("\n".join(lines))
    return f"已更新{len(CURRENT_TODOS)}个任务"


def run_create_task(
    subject: str,  # 任务主题
    description: str = "",  # 任务描述
    blockedBy: list[str] | None = None,  # 阻塞依赖列表
):
    task = create_task(subject, description, blockedBy)
    deps = f"(blockedBy:){','.join(blockedBy) if blockedBy else ''}"
    print(f"\x1b[34m创建{task.subject} {deps}\x1b[0m")
    return f"已经创建{task.id}:{task.subject}{deps}"


def run_list_tasks():
    tasks = list_tasks()
    if not tasks:
        return "暂无任务，可以使用create_task添加"
    lines = []
    for t in tasks:
        icon = {
            "pending": "等待中",
            "in_progress": "处理中",
            "completed": "已完成",
        }.get(t.status, "?")
        deps = f"(blockedBy:){','.join(t.blockedBy) if t.blockedBy else ''}"
        owner = f"[{t.owner}]" if t.owner else ""
        lines.append(f"  {icon} {t.id}: {t.subject} [{t.status}]{owner}{deps}")
    return "\n".join(lines)


def run_get_task(task_id):
    return get_task(task_id)


def run_claim_task(task_id: str):
    return claim_task(task_id)


def run_complete_task(task_id):
    return complete_task(task_id)


def run_delete_task(task_id):
    return delete_task(task_id)


# 定义调试定时任务的函数
def run_schedule_cron(
    cron: str,  # cron表达式
    prompt: str,  # 提示词
    recurring: bool = True,  # 是否循环
    durable: bool = True,  # 是否持久化
):
    result = schedule_cron(cron, prompt, recurring, durable)
    return f"已经调度{result.id}:{cron} -> {prompt}"  # type: ignore


def run_list_crons():
    # 使用锁确保并发安全，读取所有的scheduled_jobs
    with cron_lock:
        jobs = list(scheduled_jobs.values())
    if not jobs:
        return "暂无cron任务，可以使用schedule_cron添加"
    lines = []
    for job in jobs:
        tag = "循环" if job.recurring else "单次"
        dur = "持久化" if job.durable else "会话"
        lines.append(f"- {job.id}: {job.cron} {job.prompt} {tag} {dur}")
    return "\n".join(lines)


def run_cancel_cron(job_id):
    return cancel_cron(job_id)


def run_spawn_teammate(name: str, role: str, prompt: str):
    return spawn_teammate_thread(name, role, prompt)


def run_send_message(to: str, content: str):
    # 发送方固定为当前的会话身份或者说名称，不可伪造
    from_agent = current_agent.get()
    # 使用BUS消息总线发送消息
    BUS.send(from_agent, to, content)
    # 如果发给的人不是lead，并且发给的人的线程不在运行中
    if to != LEAD_NAME and not is_teammate_running(to):
        return (
            f"已从{from_agent} 写入 {to}的收件箱，但该队友未在运行"
            f"请spawn_teammate重启后才会读取消息"
        )
    return f"已从{from_agent} 发送给{to} ，内容为{content[:50]}"


def run_check_inbox():
    # 获取当前的Agent的名称
    name = current_agent.get()
    # lead和队友都只能消息自己的收件箱，避免抢走对方的消息
    msgs = consume_inbox(name)
    # 如果收件箱消息为空列表
    if not msgs:
        return f"{name}的收件箱为空"
    # 如果收件箱有消息，则格式化这些消息并返回
    return format_inbox_messages(msgs)


def run_await_teammates(names=[], timeout=TEAMMATE_WAIT_TIMEOUT):
    if current_agent.get() != LEAD_NAME:
        return "错误，仅lead可以调用await_teammates"
    return wait_for_teammates(names=names, timeout=timeout)


# 定义字典，把工具的名称和真正的处理函数关联起来
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
    "todo_write": run_todo_write,
    "load_skill": run_load_skill,
    "create_task": run_create_task,
    "list_tasks": run_list_tasks,
    "get_task": run_get_task,
    "claim_task": run_claim_task,
    "complete_task": run_complete_task,
    "delete_task": run_delete_task,
    "schedule_cron": run_schedule_cron,  # 调度定时任务
    "list_crons": run_list_crons,
    "cancel_cron": run_cancel_cron,
    "spawn_teammate": run_spawn_teammate,  # 在后台线程启动队友Agent
    "send_message": run_send_message,  # 通过MesasgeBus向队友发消息
    "check_inbox": run_check_inbox,  # 仅检查当前的Agent的自己的收件箱
    "request_shutdown": run_request_shutdown,  # LEAD领导要求队友优雅关闭
    "request_plan": run_request_plan,  # 要求队友提交计划供审核
    "submit_plan": run_submit_plan,  # 队友向队长提交计划
    "review_plan": run_review_plan,  # 队长审核队友的计划
    "await_teammates": run_await_teammates,  # 队长审核队友的计划
    "create_worktree": run_create_worktree,
    "remove_worktree": run_remove_worktree,
    "keep_worktree": run_keep_worktree,
    "connect_mcp": run_connect_mcp,
}
