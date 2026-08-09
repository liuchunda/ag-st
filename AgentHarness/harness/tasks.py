from dataclasses import dataclass, asdict
import time
import random
import json
from config import TASKS_DIR, TEXT_ENCODING


@dataclass
class Task:
    id: str  # 任务ID
    subject: str  # 任务主题
    description: str  # 任务描述
    status: str  # 任务的状态 pending in_progress completed
    owner: str | None  # 认领人 所有者 当一个任务被 创建的时候，它的owner就是None
    blockedBy: list[str]  # 阻塞任务ID列表
    worktree: str | None = None  # 绑定的git worktree名称


def _task_path(task_id: str):
    return TASKS_DIR / f"{task_id}.json"


def save_task(task: Task):
    _task_path(task.id).write_text(
        json.dumps(asdict(task), indent=2, ensure_ascii=False), encoding=TEXT_ENCODING
    )


# A2A
def create_task(subject: str, description: str, blockedBy: list[str] | None = None):
    task = Task(
        id=f"task_{int(time.time())}_{random.randint(0,9999):04d}",
        subject=subject,
        description=description,
        status="pending",
        owner=None,
        blockedBy=blockedBy or [],
    )
    save_task(task)
    return task


def list_tasks():
    return [
        Task(**json.loads(p.read_text(encoding=TEXT_ENCODING)))
        for p in sorted(TASKS_DIR.glob("task_*.json"))
    ]


# 传入task_id,返回Task类的实例
def load_task(task_id: str):
    return Task(**json.loads(_task_path(task_id).read_text(encoding=TEXT_ENCODING)))


def get_task(task_id: str):
    return json.dumps(asdict(load_task(task_id)), indent=2, ensure_ascii=False)


def can_start(task_id: str) -> bool:
    task = load_task(task_id)
    for dep_id in task.blockedBy:
        # 如果依赖的任务不存在，则返回False
        if not _task_path(dep_id).exists():
            return False
        # 如果任何一个依赖任务不是完成状态，就返回False，表示不能启动
        if load_task(dep_id).status != "completed":
            return False
    return True


def claim_task(task_id):
    from teams import current_agent

    owner = current_agent.get()
    task = load_task(task_id)
    # 如果任务状态不为pending，则无法认领
    if task.status != "pending":
        return f"任务{task.id}状态为{task.status},无法认领"
    if task.owner:
        return f"任务{task.id}已经被{task.owner}认领过了,无法认领"
    # 如果任务被依赖阻塞，则无法启动
    if not can_start(task_id):
        # 指的是未完成的依赖任务ID列表
        deps = [
            d
            for d in task.blockedBy
            if not _task_path(d).exists() or load_task(d).status != "completed"
        ]
        return f"任务被阻塞无法认领，依赖:{deps}"
    task.owner = owner
    task.status = "in_progress"
    save_task(task)
    print(f"[认领]{task.subject}-> in_progress(负责人:{owner})")
    return f"已认领{task.id}({task.subject})"


def complete_task(task_id):
    task = load_task(task_id)
    # 如果任务状态不为pending，则无法认领
    if task.status != "in_progress":
        return f"任务{task.id}状态为{task.status},无法完成"
    task.status = "completed"
    save_task(task)
    # 找到因本任务而解锁，现在可以开始的任务
    # 准确的话，找到现在已经解锁可以执行的任务
    unblocked = [
        t.subject
        for t in list_tasks()
        if t.status == "pending" and t.blockedBy and can_start(t.id)
    ]
    print(f"[完成] {task.subject}√")
    msg = f"已完成{task_id}({task.subject})"
    if unblocked:
        msg += f"\n已解阻: {','.join(unblocked)}"
        print(f"\n已解阻: {','.join(unblocked)}")
    return msg


def delete_task(task_id):
    task_path = _task_path(task_id)
    if not task_path.exists():
        return f"任务{task_id}不存在，无法删除"
    task = load_task(task_id)
    dependents = []
    for t in list_tasks():
        if task_id in t.blockedBy:
            dependents.append(t)
    # 如果有依赖任务，则判断是否可以删除
    if dependents:
        incompleted_deps = [t for t in dependents if t.status != "completed"]
        if incompleted_deps:
            dep_info = ", ".join([f"{t.id}({t.subject})" for t in incompleted_deps])
            return f"任务{task_id}被 依赖且未完成，无法删除，依赖的依赖:{dep_info}"
        print(f"[提醒] 任务{task_id}被已经完成的任务依赖，将清理依赖关系")
        for t in dependents:
            t.blockedBy = [d for d in t.blockedBy if d != task_id]
            save_task(t)
            print(f"- 已经清理了{t.id}依赖")

    # 删除文件
    task_path.unlink()
    msg = f"已经删除任务{task_id}({task.subject})"
    print(msg)
    return msg


# 定义一个返回未被认领且所有的依赖都已经完成的任务的函数
def scan_unclaimed_tasks():
    # 列出所有的任务，然后对每个任务进行判断(状态为pending,负责人为空，依赖任务都已经完成)
    return [
        task
        for task in list_tasks()
        if task.status == "pending" and not task.owner and can_start(task.id)
    ]
