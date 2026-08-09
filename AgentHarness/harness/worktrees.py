import re
from config import WORKTREES_DIR, WORKDIR, TEXT_ENCODING
import subprocess
import json
import time
from tasks import load_task, save_task

# 合法 worktree 名称的正则表达式：只允许字母、数字、点、下划线、连字符，长度 1 到 64
VALID_WT_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def validate_worktree_name(name):
    if not name:
        return "worktree名称不能为空"
    if name in (".", ".."):
        return f"{name}不是合法的worktree名称"
    if not VALID_WT_NAME.match(name):
        return f"无效的worktree名称:{name}" f"仅允许字母、数字、下划线、点、连字符"
    return None


def run_git(args):
    from utils import decode_subprocess_output

    try:
        result = subprocess.run(
            ["git"] + args, cwd=WORKDIR, capture_output=True, timeout=60
        )
        out = decode_subprocess_output(
            (result.stdout or b"") + (result.stderr or b"")
        ).strip()
        out = out[:500000] if out else "(无输出)"
        return result.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False


def log_event(event_type, worktree_name, task_id=""):
    event = {
        "type": event_type,
        "worktree": worktree_name,
        "task_id": task_id,
        "ts": time.time(),
    }
    events_file = WORKTREES_DIR / "events.jsonl"
    with open(events_file, "a", encoding=TEXT_ENCODING) as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# 创建任务后，LLM可能认为这个任务需要在一个有意思工作树下进行，就再创建一个工作树并且和此任务进行绑定
# 以后如果有Agent认领到这个任务后，就会切换到任务指定的工作区下面进行工作
def bind_task_to_worktree(task_id: str, worktree_name: str):
    """仅写入task.worktree,不改变status"""
    # 加载task_id指定的任务
    task = load_task(task_id)
    # 设置任务worktree字段
    task.worktree = worktree_name
    # 保存任务
    save_task(task)
    print(f"\x1b[33m 绑定 {task.subject} -> worktree:{worktree_name} \x1b[0m")


def run_create_worktree(name, task_id=""):
    err = validate_worktree_name(name)
    if err:
        return f"错误: {err}"
    path = WORKTREES_DIR / name
    if path.exists():
        return f"worktree:{name}已经存在于{path}"
    # git worktree add path -b wt/{name} HEAD
    ok, result = run_git(["worktree", "add", str(path), "-b", f"wt/{name}", "HEAD"])  # type: ignore
    if not ok:
        return f"Git错误:{result}"
    # 如果传入了任务ID
    if task_id:
        bind_task_to_worktree(task_id, name)
    log_event("create", name, task_id)
    print(f"\x1b[33m  [WorkTree] 已经创建{name} @ {path} \x1b[0m")
    return f"worktree {name} 已经创建于 {path}"


def _count_worktree_changes(path):
    from utils import decode_subprocess_output

    try:
        # 以列表的形式传递命令行的参数，porcelain的意思是git专门为了脚本解析输出的格式 机器可读的固定形式
        result1 = subprocess.run(["git", "status", "--porcelain"])
        status_out = decode_subprocess_output(
            (result1.stdout or b"") + (result1.stderr or b"")
        ).strip()
        # 统计非空的变更行数
        files = len([line for line in status_out.splitlines() if line.strip()])
        # git log @{push}..HEAD --oneline
        # HEAD当前分支最新的提交  @{push} 上游推送目标 就是当前分支配置的远程跟踪分支
        # .@{push}..HEAD表示从@{push}之后到HEAD之间所有的提交
        result2 = subprocess.run(["git", "log", "@{push}..HEAD", "--oneline"])
        log_out = decode_subprocess_output(
            (result2.stdout or b"") + (result2.stderr or b"")
        ).strip()
        # 统计非空的变更行数
        commits = len([line for line in log_out.splitlines() if line.strip()])
        return files, commits
    except Exception:
        return -1, -1


def run_remove_worktree(name, discard_changes=False):
    err = validate_worktree_name(name)
    if err:
        return f"错误: {err}"
    path = WORKTREES_DIR / name
    if not path.exists():
        return f"worktree:{name}不存在{path}"
    # 如果不是强制丢弃，检查状态
    if not discard_changes:
        files, commits = _count_worktree_changes(path)
        if files < 0:
            return f"无法验证worktree {name}的状态" "请设置discard_changes=True强制删除"
        # 如果有未提交或未推送
        if files > 0 or commits > 0:
            return (
                f"worktree {name} 有{files}个未提交的文件"
                f"{commits}个未推送提交"
                "请设置discard_changes=True强制删除"
                f"或使用keep_worktree保留供审查"
            )
    # 删除worktree目录，--force是不行worktree一个参数，表示强行删除
    ok, _ = run_git(["worktree", "remove", str(path), "--force"])  # type: ignore
    if not ok:
        return f"删除worktree {name}目录失败"
    # 删除关联的分支
    run_git(["branch", "-D", f"wt/{name}"])
    log_event("remove", name)
    print(f"\x1b[33m WorkTree 已经删除 :{name} \x1b[0m")
    return f"WorkTree 已经删除 :{name}"


def keep_worktree(name):
    err = validate_worktree_name(name)
    if err:
        return f"错误: {err}"
    log_event("keep", name)
    print(f"\x1b[33m WorkTree{name} 已保留 \x1b[0m")
    return f"WorkTree {name}保留供审查"


def run_keep_worktree(name: str):
    return keep_worktree(name)
