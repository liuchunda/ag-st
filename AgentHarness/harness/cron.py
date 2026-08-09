import json
import random
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from config import TEXT_ENCODING, DURABLE_PATH


@dataclass
class CronJob:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool


# 定义锁对象，保证线程安全
cron_lock = threading.Lock()
# 定义调度中的任务字典，key为计划任务的ID，值为CronJob对象实例
scheduled_jobs: dict[str, CronJob] = {}
# 定时任务执行队列，存储等待消费的CRONjob对象
cron_queue: list[CronJob] = []
# 记录各个任务上一次触发的时间，key为任务ID,值为时间戳
_last_fired: dict[str, str] = {}


def _validate_cron_field(field: str, low: int, high: int):
    # 如果值是*，则直接较验通过
    if field == "*":
        return None
    # 如果是以*/开头，表示是隔多长时间一次 */15
    if field.startswith("*/"):
        step_str = field[2:]
        if not step_str.isdigit():
            return f"无效步长:{field}"
        if int(step_str) <= 0:
            return f"步长必须大于0:{field}"
        return None
    if "," in field:  # 1,5,8
        for part in field.split(","):
            # 在这个地方会递归较验每个值
            err = _validate_cron_field(part.strip(), low, high)
            if err:
                return err
        return None
    if "-" in field:  # 1-5
        parts = field.split("-", 1)
        if not parts[0].isdigit() or not parts[1].isdigit():
            return f"无效范围:{field}"
        a, b = int(parts[0]), int(parts[1])
        if a < low or a > high or b < low or b > high:
            return f"范围{field}超出了{low}-{high}"
        if a > b:
            return f"范围起始值要小于结束值:{field}"
    if not field.isdigit():
        return f"无效字段:{field}"
    val = int(field)
    if val < low or val > high:
        return f"值{val}超出{low}-{high}"
    return None


# * * * * *
def validate_cron(cron_expr: str):
    # 拆分cron表达式为字段
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return f"cron需要5个字段，实际上传递了{len(fields)}个"
    # 指定各个字段的上下界，或者说取值范围
    bounds = [
        (0, 59),
        (0, 23),
        (1, 31),
        (1, 12),
        (0, 6),
    ]
    names = ["分", "时", "日", "月", "周"]
    for field, (low, high), name in zip(fields, bounds, names):
        err = _validate_cron_field(field, low, high)
        if err:
            return f"{name}:{err}"
    return None


def save_durable_jobs():
    # 只保存标记为durable为True的计划任务
    durable = [asdict(job) for job in scheduled_jobs.values() if job.durable]
    DURABLE_PATH.write_text(
        json.dumps(durable, indent=2, ensure_ascii=False), encoding=TEXT_ENCODING
    )


def schedule_cron(cron: str, prompt: str, recurring: bool, durable: bool):
    # 校验cron表格式的合法性
    err = validate_cron(cron)
    if err:
        return err
    job = CronJob(
        id=f"cron_{random.randint(0,999999):06d}",  # 任务ID
        cron=cron,
        prompt=prompt,
        recurring=recurring,
        durable=durable,
    )
    # 写入计划任务池，线程安全
    with cron_lock:
        scheduled_jobs[job.id] = job
    if durable:
        save_durable_jobs()
    print(f"\x1b[35m[注册计划任务Cron]{job.id} {cron} -> {prompt}\x1b[0m")
    return job


def load_durable_jobs():
    if not DURABLE_PATH.exists():
        return
    jobs = json.loads(DURABLE_PATH.read_text(encoding=TEXT_ENCODING))
    for job in jobs:
        job = CronJob(**job)
        err = validate_cron(job.cron)
        if err:
            print(f"跳过无效的任务{job.id}:{err}")
            continue
        scheduled_jobs[job.id] = job
    valid_jobs = [job for job in jobs if job["id"] in scheduled_jobs]
    if valid_jobs:
        print(f"\x1b[35m [CRON]已经加载了{len(valid_jobs)}个持久化任务\x1b[0m")


def _cron_field_match(field: str, value: int):
    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(_cron_field_match(f.strip(), value) for f in field.split(","))
    if "-" in field:
        low, high = field.split("-", 1)
        return int(low) <= value <= int(high)
    return value == int(field)


# 检查给定的时间和当前的时间是否匹配
def cron_matchs(cron_expr: str, dt: datetime):
    # 将cron表达式去掉两边的空格，并按空格分割，得到五段
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False
    # 分 时 日 月 星期
    minute_field, hour_field, day_field, month_field, week_field = fields
    # 计算符合cron语法的星期数字 python里的weekday()返回的值 0表示周一 123456
    # 在cron表达式里面0-6,0表示周日 0123456
    day_of_week_val = (dt.weekday() + 1) % 7
    minute_match = _cron_field_match(minute_field, dt.minute)
    hour_match = _cron_field_match(hour_field, dt.hour)
    day_match = _cron_field_match(day_field, dt.day)
    month_match = _cron_field_match(month_field, dt.month)
    week_match = _cron_field_match(week_field, day_of_week_val)
    # 如果分钟，小时，月份任何一个不匹配则直接返回False
    if not (minute_match and hour_match and month_match):
        return False
    month_unconstrained = month_field == "*"
    week_unconstrained = week_field == "*"
    if month_unconstrained or week_unconstrained:
        return True
    if month_unconstrained:
        return week_match
    if week_unconstrained:
        return day_match
    return day_match or week_match


# cron调度主循环
def cron_scheduler_loop():
    while True:
        # 每秒调度一次
        time.sleep(1)
        # 获取当前的时间
        now = datetime.now()
        # 获取分钟粒度的时间戳标识
        minute_marker = now.strftime("%Y-%m-%d %H:%M")
        with cron_lock:
            # 遍历当前所有的计划任务
            for job in list(scheduled_jobs.values()):
                # */2 * * * * 判断当前的时间和任务的cron表达式是否匹配
                if cron_matchs(job.cron, now):
                    # 判断此定时任务在这个当前的分钟时间内是否已经触发过了，不再触发了
                    if _last_fired.get(job.id) != minute_marker:
                        cron_queue.append(job)
                        _last_fired[job.id] = minute_marker
                        print(f"\x1b[35m[Cron]触发 {job.id} -> {job.prompt}\x1b[0m")
                    # 如果任务不需要循环执行，触发一次就移除
                    if not job.recurring:
                        scheduled_jobs.pop(job.id, None)
                        if job.durable:
                            save_durable_jobs()


# 启动cron调度器
def start_cron_scheduler():
    # 1.先加载持续化任务
    load_durable_jobs()
    # 开启一个调度线程
    threading.Thread(target=cron_scheduler_loop, daemon=True).start()
    print(f"\x1b[35m [CRON]调度线程已经启动\x1b[0m")


# 判断队列是否是空
def has_cron_queue():
    with cron_lock:
        return bool(cron_queue)


# 定义队列处理器主循环函数，参数为调度执行函数和锁
def _queue_processor_loop(dispatch_fn, agent_lock):
    while True:
        time.sleep(0.2)
        # 如果没有可消息的定时队列，跳过本次循环
        if not has_cron_queue():
            continue
        # 如果未能获取agent锁则跳过本次循环
        if not agent_lock.acquire(blocking=False):
            continue
        try:
            if not has_cron_queue():
                continue
            print(f"\x1b[35m[Cron队列处理器]投递定时任务\x1b[0m")
            # 执行传入的调试分发函数
            dispatch_fn()
        finally:
            agent_lock.release()


def start_queue_processor(run_agent_turn_locked, agent_lock):
    threading.Thread(
        target=_queue_processor_loop,
        args=(run_agent_turn_locked, agent_lock),
        daemon=True,
    ).start()
    print(f"\x1b[35m[Cron队列处理器]已经启动\x1b[0m")


# 消费cron_queue列表
def consume_cron_queue():
    with cron_lock:
        # 备份所有被触发的任务
        fired = list(cron_queue)
        # 清空定时任务队列
        cron_queue.clear()
    return fired


def cancel_cron(job_id):
    # 从任务池中删除该 任务
    with cron_lock:
        job = scheduled_jobs.pop(job_id, None)
    if not job:
        return f"未找到任务{job_id}"
    # 如果任务需要持久化，则存硬盘
    if job.durable:
        save_durable_jobs()
    print(f"[Cron取消任务] {job_id}")
    return f"[Cron取消任务] {job_id}"
