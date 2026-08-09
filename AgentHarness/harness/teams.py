import threading
import json
import time
import random
from contextvars import ContextVar
from pathlib import Path
from config import (
    client,
    MODEL_ID,
    DEFAULT_MAX_TOKENS,
    MAILBOX_DIR,
    TEXT_ENCODING,
    MAILBOX_BACKUP_DIR,
    TEAMMATE_WAIT_TIMEOUT,
    WAIT_POLL_INTERVAL,
    WORKTREES_DIR,
)
from history import repair_message_chain
from utils import assistant_message_dict
from dataclasses import dataclass, field
import time
from tasks import scan_unclaimed_tasks, claim_task, load_task, complete_task

# 主管的名称或者负责人的名称，就是我们的主Agent
LEAD_NAME = "lead"
# 队友LLM调用的最大轮数
TEAMMATE_MAX_ROUNDS = 10
# 当前正在活跃的子Agent线程字典 key队友的名称 value是线程对象
active_teammates: dict[str, threading.Thread] = {}
# 文件读写锁
_bus_lock = threading.Lock()
# 当前的Agent名称 ContextVar就是为了实现线程间变量隔离
current_agent: ContextVar[str] = ContextVar("current_agent", default="lead")
# 已经spawn,但尚未收到type=result的队友
pending_teammate_results: set[str] = set()


# MessageBus  send msg_type 消息的类型，有两种，一种是普通消息message,另一种叫协议消息
# ProtocolState  type 协议消息类型就是
class MessageBus:
    def send(
        self,
        from_agent: str,  # 发送者
        to_agent: str,  # 接收者
        content: str,  # 消息内容
        msg_type: str = "message",  # 消息的类型，默认message
        metadata: dict | None = None,  # 附加的元数据，默认为None
    ):
        # 构造消息内容的字典
        msg = {
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "type": msg_type,
            "ts": time.time(),
            "metadata": metadata or {},
        }
        # 构建teammate队友收件箱文件的文件路径
        inbox = MAILBOX_DIR / f"{to_agent}.jsonl"
        # inbox_backup = MAILBOX_BACKUP_DIR / f"{to_agent}.jsonl"
        # 因为我们有多队友Agent线程可能都需要向lead的收件箱文件里发消息，为了避免冲突，添加一个文件锁
        with _bus_lock:
            # 以追加模式写入收件条
            with open(inbox, "a", encoding=TEXT_ENCODING) as f:
                # 将消息写为JSON字符串，每条一行
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            # 以追加模式写入收件条
            # with open(inbox_backup, "a", encoding=TEXT_ENCODING) as f:
            #    # 将消息写为JSON字符串，每条一行
            #    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        print(
            f"\x1b[33m [总线] {from_agent}->{to_agent} [{msg_type}]:{content[:50]}  \x1b[0m"
        )

    # 读取某个Agent收件箱里的消息
    def read_inbox(self, agent: str):
        # 构建teammate队友收件箱文件的文件路径
        inbox = MAILBOX_DIR / f"{agent}.jsonl"
        # read_index和send共用锁，避免读写竞态丢消息
        with _bus_lock:
            # 如果收件箱文件不存在，则返回空列表
            if not inbox.exists():
                return []
            # 读取所有的消息，每行解析为一个JSON字典
            msgs = [
                json.loads(line)
                for line in inbox.read_text(encoding=TEXT_ENCODING).splitlines()
                if line.strip()
            ]
            # 读取完后删除收件箱文件
            inbox.unlink()
        return msgs


# 创建MessageBus类的实例
BUS = MessageBus()


@dataclass
class ProtocolState:
    # 请求的唯一标识符
    request_id: str
    # 协议的类型
    type: str  # shutdown plan_approval
    # 请求协议发送方
    sender: str
    # 请求协议目标对象或者接收方
    target: str
    # 状态  等待中 审批通过 拒绝通过
    status: str  # pending approved rejected
    # 附加的数据和信息
    payload: str
    # 创建时间
    created_at: float = field(default_factory=time.time)


# 用于存储所有的挂起的协议请求，键为请求ID，值为协议状态对象
pending_requests: dict[str, ProtocolState] = {}
# 空闲超时时间单位是秒
IDLE_TIMEOUT = 120
# 空闲轮询时间间隔单位是秒
IDLE_POLL_INTERVAL = 2


def _process_teammate_inbox(
    teammate_name: str, inbox: list[dict], messages  # 队友的名字  # 收件箱的消息列表
):  # 对话消息列表
    # 标记是否需要终止(是否收到了来自于主管的关机的请求)
    should_stop = False
    # 用于保存非协议消息
    non_protocol_msgs = []
    for msg in inbox:
        # 获取收件箱里的消息类型
        msg_type = msg.get("type", "message")
        meta = msg.get("metadata", {})
        req_id = meta.get("request_id", "")
        # 如果收到了来自主管的关机请求 协议消息和普通消息是互斥的
        if msg_type == "shutdown_request":
            # 进行关机前的清理工作，清理完成后
            # 先给主管回复一个同意关闭的响应
            BUS.send(
                teammate_name,  # 自己这个队友的名字 自己的名字
                LEAD_NAME,  # 主管=主Agnet=主代理=领导=主线程=队长 组员=队友
                "同意关闭，正在优雅关闭",  # 消息内容
                "shutdown_response",  # 消息类型
                {"request_id": req_id, "approve": True},  # 元数据，携带请求ID和批准信号
            )
            # 把关机标记为True
            should_stop = True
            # 跳出循环，因为一旦马上要关机了，后续消息不需要处理了
            break
        # 如果收到的收件箱消息是计划审批响应
        if msg_type == "plan_approval_response":
            # 获取是否批准
            approve = meta.get("approve", False)
            if approve:
                messages.append(
                    {"role": "user", "content": "[计划已经批准] 请继续执行任务"}
                )
            else:
                messages.append(
                    {"role": "user", "content": f"[计划被拒绝] 反馈:{msg['content']}"}
                )
            continue
        non_protocol_msgs.append(msg)
    return should_stop, non_protocol_msgs


# 获取队友 LLM 上下文，只取最新 tail 条消息，并修复 tool 链
def _teammate_llm_context(messages: list, tail: int = 20) -> list:
    # 如果消息数量大于 tail，则取最后 tail 条，否则全部取
    window = messages[-tail:] if len(messages) > tail else list(messages)
    # 修复 tool 链，防止 API 错误，返回修复后的窗口消息
    return repair_message_chain(window)


def include_shutdown(agent_name, inbox):
    shutdown = False
    for msg in inbox:
        if msg.get("type") == "shutdown_request":
            req_id = msg.get("metadata", {}).get("request_id", "")
            BUS.send(
                agent_name,
                LEAD_NAME,
                "正在优雅关闭",
                "shutdown_response",
                {"request_id": req_id, "approve": True},
            )
            print(f"\x1b[35m [协议] {agent_name} 在idle的时候同意关闭{req_id}  \x1b[0m")
            shutdown = True
    return shutdown


# 空闲轮询函数，用于处理队友的空闲状态
def idle_poll(agent_name: str, messages: list, wt_ctx: dict | None = None):
    # 轮询IDLE_TIMEOUT秒，分为若干小轮，每一次暂停IDLE_POLL_INTERVAL  120/5
    for _ in range(IDLE_TIMEOUT // IDLE_POLL_INTERVAL):
        # 暂停IDLE_POLL_INTERVAL秒
        time.sleep(IDLE_POLL_INTERVAL)
        # 读取agent_name的收件箱的消息
        inbox = BUS.read_inbox(agent_name)
        # 如果收件非空，说明有别的人给自己发消息了
        if inbox:
            # 这个地方在找有没有关机的消息，如果有直接返回，直接让这个队友关机了，后面消息就不处理了
            # 如果没有关机的消息，就添加消息后继续工作
            shutdown = include_shutdown(agent_name, inbox)
            if shutdown:
                return "shutdown"
            else:
                messages.append(
                    {
                        "role": "user",
                        "content": f"<inbox>{json.dumps(inbox,ensure_ascii=False)}</inbox>",
                    }
                )
                print(
                    f"\x1b[36m [Idle] {agent_name} 在空闲的收到{len(inbox)}条消息 \x1b[0m"
                )
                # 因为收了新的消息，可能是主管给了派了新的工作，那么要返回work进入工作状态
                return "work"
        # 如果没有人给当前空闲的Agent发送消息
        # 检查当前是否有未被认认领的任务
        unclaimed = scan_unclaimed_tasks()
        # 如果有可认领的任务
        if unclaimed:
            # 取出第一个可以认领的任务
            task = unclaimed[0]
            # 认领任务
            result = claim_task(task.id)
            # 如果当前这个队友成功认领了任务，
            if result.startswith("已认领"):
                # 判断这个任务有没有对应的worktree
                if task.worktree:
                    # 构造工作目录路径
                    wt_path = WORKTREES_DIR / task.worktree
                    if wt_ctx is not None:
                        wt_ctx["path"] = str(wt_path)
                elif wt_ctx is not None:
                    wt_ctx["path"] = None
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"<auto-claimed>任务{task.id}:{task.subject}</auto-claimed>"
                        ),
                    }
                )
                print(
                    f"\x1b[32m [Idle] {agent_name} 自动认领成功: {task.subject} \x1b[0m"
                )
                return "work"
            else:
                print(f"\x1b[33m [Idle] {agent_name} 认领失败: {result} \x1b[0m")
    # 如果超时轮询结束仍然未收到新的消息或者任务，打印超时提示
    print(f"\x1b[33m Idle {agent_name} 超时 {IDLE_TIMEOUT}秒，自动关闭  \x1b[0m")
    return "timeout"


# 队友=子Agent=子代理=子线程
# 启动一个队友线程函数
def spawn_teammate_thread(name: str, role: str, prompt: str):
    if name == LEAD_NAME:
        return f"错误：不能使用保留的Agent名称:{LEAD_NAME}"
    # 查看当前的名称的队友线程是否存在
    existing = active_teammates.get(name)
    # 如果线程存在，并且线程是活着的状态
    if existing and existing.is_alive():
        return f"队友{name}已经存在并且仍在运行"
    if existing:
        # 如果线程对象存在，但已经不在活动了，将它移除掉
        active_teammates.pop(name, None)
        print("\x1b[33m [队友]{name}旧线程已经退出，允许重新启动  \x1b[0m")
    teammate_system = (
        f"你是{name},角色为{role}"
        f"你将在Windows CMD环境下执行任务，使用CMD命令完成任务"
        f"你要检查收件箱里的协议消息(shutdown_request)等"
        f"使用工具完成任务，你可以在空闲的时候从看板列出的任务中自动认领任务"
        f"如果任务绑定了worktree,bash/read/write/edit/glob都会在该目录下执行"
    )

    # 其实现在我们这个队友也是一次性的，执行完一次任务就销毁了。
    def run():
        from tools.executor import execute_tool
        from tools.schema import TOOLS
        from tools.handlers import run_bash, run_read, run_write, run_edit, run_glob

        # worktree工作目录上下文 (认领绑定任务后会自动切换)
        wt_ctx: dict[str, str | None] = {"path": None}

        # 通过此方法获取到路径
        def _wt_cwd():
            p = wt_ctx["path"]
            # 再把 p包装成Path的路径实例
            return Path(p) if p else None

        def teammate_execute_tool(tname, args):
            cwd = _wt_cwd()
            if tname == "bash":
                return run_bash(
                    args.get("command", ""),
                    run_in_background=bool(args.get("run_in_background", False)),
                    cwd=cwd,  # 指定工作目录
                )
            elif tname == "read_file":
                return run_read(args.get("path"), limit=args.get("limit"), cwd=cwd)
            elif tname == "write_file":
                return run_write(args.get("path"), content=args.get("content"), cwd=cwd)
            elif tname == "edit_file":
                return run_edit(
                    args.get("path"),
                    old_text=args.get("old_text"),
                    new_text=args.get("new_text"),
                    cwd=cwd,
                )
            elif tname == "glob":
                return run_glob(args.get("pattern"), cwd=cwd)
            elif tname == "claim_task":
                result = claim_task(args.get("task_id", ""))
                if result.startswith("已认领"):
                    # 如果认任务成功，则加载任务
                    task = load_task(args["task_id"])
                    # 如果认领任务成功，如果任务绑定了worktree,更新worktree目录路径
                    wt_ctx["path"] = (
                        str(WORKTREES_DIR / task.worktree) if task.worktree else None
                    )
                return result
            elif tname == "complete_task":
                # 当完成任务后要清空当前的workTree路径
                result = complete_task(args.get("task_id", ""))
                wt_ctx["path"] = None
                return result
            else:
                return execute_tool(tname, args)

        # 绑定当前线程的Agent名称，防止伪造from_agent 每个Agent Teammate线程都会独立拥有这样的一份变量的值，相互之间不冲突，不影响，不能篡改
        identity_token = current_agent.set(name)
        # 初始化消息列表
        # 现在任务是lead通过提示词下发的
        messages = [{"role": "user", "content": prompt}]
        # 记录退出的原因
        exit_reason = ""
        try:
            while True:
                if len(messages) <= 3:
                    # 如果消息数量不超过3条，插入身份声明消息
                    messages.insert(
                        0,
                        {
                            "role": "user",
                            "content": (
                                f"<identity>你是{name},角色为{role},请继续你的工作</identity>"
                            ),
                        },
                    )
                # 初始化是否退出循环的标志
                should_shutdown = False
                # 进入最大循环轮数控制
                for _ in range(TEAMMATE_MAX_ROUNDS):
                    # 读取自己的收件箱消息
                    inbox = BUS.read_inbox(name)
                    # 如果收件箱有消息，则进行处理
                    if inbox:
                        # 处理消息 ，消息分为协议要求和非协议消息两种
                        should_stop, non_protocol_msgs = _process_teammate_inbox(
                            name, inbox, messages
                        )
                        # 如果收到关闭信号，则设置退出标志 并退出循环
                        if should_stop:
                            should_shutdown = True
                            break
                        # 如果此消息非协议消息，也就是普通消息，将其添加到对话消息列表中
                        if non_protocol_msgs:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": (
                                        f"<inbox>{json.dumps(non_protocol_msgs,ensure_ascii=False)}</inbox>"
                                    ),
                                }
                            )
                    # 通过 OpenAI 客户端请求 LLM 产生回复
                    try:
                        response = client.chat.completions.create(
                            model=MODEL_ID,
                            messages=[
                                {"role": "system", "content": teammate_system},
                                *_teammate_llm_context(messages),
                            ],
                            tools=TOOLS,  # type: ignore
                            max_tokens=DEFAULT_MAX_TOKENS,
                        )
                    # 捕捉 API 调用异常，记录错误与退出原因
                    except Exception as e:
                        exit_reason = f"LLM 错误: {type(e).__name__}: {e}"
                        print(f"  \x1b[31m[队友] {name} {exit_reason}\x1b[0m")
                        should_shutdown = True
                        break
                    assistant = response.choices[0].message
                    # 获取到大模型返回的消息后一定要把返回的消息添加到对话历史
                    messages.append(assistant_message_dict(assistant))
                    # 如果 assistant 没有调用任何工具，跳出当前大循环
                    if not assistant.tool_calls:
                        break

                    # 遍历所有工具调用，执行每一个工具
                    for tool_call in assistant.tool_calls:
                        # 获取工具名称
                        tname = tool_call.function.name  # type: ignore
                        # 解析工具参数
                        args = json.loads(tool_call.function.arguments or "{}")  # type: ignore
                        # 执行工具（含 worktree cwd 切换）
                        output = teammate_execute_tool(tname, args)
                        # 回复工具调用的结果消息
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": output,
                            }
                        )
                # 如果应该退出主循环，跳出来外层While True
                if should_shutdown:
                    break
                # 如果现在不关机，进入空闲轮询
                idle_result = idle_poll(name, messages, wt_ctx)
                # 如果要关机的话就跳出外层循环
                if idle_result == "shutdown":
                    break
                # 如果长时间未响应，设置超时退出的原因并且关机
                if idle_result == "timeout":
                    exit_reason = f"idle超时{IDLE_TIMEOUT}"
                    break
            summary = exit_reason or "完成"
            for msg in reversed(messages):
                if msg.get("role") == "assistant" and msg.get("content"):
                    content = msg["content"]
                    if isinstance(content, str) and content.strip():
                        summary = content
                        break
            # 此处是队友给队长发了消息，队长不一定现在就能看到
            BUS.send(name, LEAD_NAME, summary, "result")
            print(f"\x1b[32m [队友]{name}已经结束  \x1b[0m")
        finally:
            current_agent.reset(identity_token)
            active_teammates.pop(name, None)

    thread = threading.Thread(target=run, daemon=True)
    active_teammates[name] = thread
    # 标记待回收的result
    pending_teammate_results.add(name)
    thread.start()
    print(f"\x1b[36m 队友{name}已经启动，角色为{role} prompt为{prompt} \x1b[0m")
    return f" 队友{name}已经启动，角色为{role} prompt为{prompt},完成后将向lead发送result,可用await_teammates等待"


def is_teammate_running(name: str):
    thread = active_teammates.get(name)
    # 判断线程对象是否存在，并且线程是否存活
    return thread is not None and thread.is_alive()


def consume_inbox(agent_name: str):
    # 读取agent_name的收箱件里的消息
    msgs = BUS.read_inbox(agent_name)
    if not msgs:
        return []
    return msgs


# 将收件箱的消息格式化为文本字符串
def format_inbox_messages(msgs: list[dict]):
    lines = []
    for m in msgs:
        msg_type = m.get("type", "message")
        meta = m.get("metadata", {})
        req_id = meta.get("request_id", "")
        header = f"来自{m['from']} [{msg_type}]"
        if req_id:
            header += f" request_id={req_id}"
        lines.append(f"{header}: {m['content'][:200]}")
    return "[收件箱]\n" + "\n".join(lines)


# 现在有两种协议消息
# 关机 关机请求是队长发起的，发起的时候状态为pending,队友收到关机消息，会发发送一个通过的关机响应给队长，队长收到后会把协议改为approved
# 计划审批 计划审批是队友发起的，发起的的时候状态为pending,队长收到这个消息后会发一个plan_approval_response响应给队友，队友收到消息后
# 匹配响应，根据request_id关联并校验响应类型
def match_response(response_type, request_id, approve):
    # 通过request_id获取协议状态
    state = pending_requests.get(request_id)
    if not state:
        print(f"\x1b[33m [协议] 未知request_id:{request_id}  \x1b[0m")
        return
    if state.type == "shutdown" and response_type != "shutdown_response":
        print(
            f"\x1b[33m [协议]类型不匹配，期望  shutdown_response\x1b[0m"
            f"实际得到的是{response_type}"
        )
        return
    if state.type == "plan_approval" and response_type != "plan_approval_response":
        print(
            f"\x1b[33m [协议]类型不匹配，期望  plan_approval_response\x1b[0m"
            f"实际得到的是{response_type}"
        )
        return
    if state.status != "pending":
        print(f"\x1b[33m [协议]{request_id}已经是{state.status},忽略重复响应\x1b[0m")
        return
    # 根据approve来判断是通过还是拒绝
    state.status = "approved" if approve else "rejected"
    icon = "√" if approve else "×"
    color = "32" if approve else "31"
    print(
        f"\x1b[{color}m [协议] {state.type} {icon} "
        f"{request_id}:{state.status}\x1b[0m"
    )


def _mark_results_received(msgs):
    for msg in msgs:
        if msg.get("type") == "result":
            sender = msg.get("from", "")
            if sender in pending_teammate_results:
                pending_teammate_results.discard(sender)
                print(f"\x1b[33m [屏障] 已经收到了{sender} 的result  \x1b[0m")


def consume_lead_inbox(route_protocol: bool = True):
    # 读取队长的消息列表
    msgs = BUS.read_inbox(LEAD_NAME)
    if not msgs:
        return []
    _mark_results_received(msgs)
    # 如果需要路由协议响应
    if route_protocol:
        for msg in msgs:
            meta = msg.get("metadata", {})
            # 请求ID
            req_id = meta.get("request_id", "")
            # 获取消息类型
            msg_type = msg.get("type", "")
            # 如果有请求ID,并且消息类型是以_response结尾的，说这个一个针对前面一个请求的响应
            if req_id and msg_type.endswith("_response"):
                # 获取是否审批通过
                approve = meta.get("approve", False)
                # 进行路由协议响应
                match_response(msg_type, req_id, approve)

    return msgs


# 读取主管收到的消息并且写入消息列表中
def inject_lead_inbox(messages: list):
    # 调用consume_lead_inbox读取lead收件箱消息，开启路由协议
    inbox = consume_lead_inbox(route_protocol=True)
    if not inbox:
        return 0
    messages.append({"role": "user", "content": format_inbox_messages(inbox)})
    print(f"\x1b[33m  [收件箱] 向{LEAD_NAME}注入{len(inbox)}条消息 \x1b[0m")
    return len(inbox)


# 生成新的请求ID
def new_request_id():
    return f"req_{random.randint(0,999999):06d}"


# 请求队友优雅关机，向其发送关机协议消息
def run_request_shutdown(teammate: str):
    # 生成一个新的唯一的请求ID
    req_id = new_request_id()
    # 在pending_requests里面记录关机请求的protocol协议状态
    # shutdown协议的类型 的发请求的时候消息的类型shutdown_request，在接收响应的时候shutdown_response
    pending_requests[req_id] = ProtocolState(
        request_id=req_id,  # 请求编号
        type="shutdown",  # 协议类型
        sender=LEAD_NAME,  # 发起者名称
        target=teammate,  # 队友的名称
        status="pending",  # 当前的状态为等待中 等待处理
        payload="",
    )
    # 主管向队友发送关机请求消息，包含了请求ID
    BUS.send(
        LEAD_NAME, teammate, "请优雅关闭", "shutdown_request", {"request_id": req_id}
    )
    print(f"\x1b[35m [协议] shutdown_request ->{teammate} ({req_id})\x1b[0m")
    return f"已向{teammate} 发送关闭请求(req_id:{req_id})"


def run_request_plan(teammate: str, task: str):
    # 队长向队友的邮箱发送请求，要求其提交 计划，消息类型为message
    BUS.send(LEAD_NAME, teammate, f"请提交计划:{task}", "message")
    return f"LEAD已经要求{teammate}提交计划"


# 队友向LEAD提交计划供审核
def run_submit_plan(from_name: str, plan: str):
    from_name = current_agent.get()
    # 创建一个新的计划审批的请求ID
    req_id = new_request_id()
    # 保存本次请求ID和请求协议对象的状态
    pending_requests[req_id] = ProtocolState(
        request_id=req_id,  # 请求ID
        type="plan_approval",  # 协议类型为 计划审批
        sender=from_name,  # 队友
        target=LEAD_NAME,  # 队长
        status="pending",  # 状态默认为等待审批
        payload=plan,  # 计划的内容
    )
    # 队友通过BUS向队长发送计划审核消息
    BUS.send(
        from_name, LEAD_NAME, plan, "plan_approval_request", {"request_id": req_id}
    )
    return f"计划{req_id}已经提交给队长，等待审批中..."


# LEAD对队友提交的计划进行审批(通过或拒绝)并进行响应
def run_review_plan(request_id: str, approve: bool, feedback: str = ""):
    # 从字典中获取 请求ID对应的协议状态
    state = pending_requests.get(request_id)
    if not state:
        return f"未找到请求{request_id}"
    if state.status != "pending":
        return f"请求{request_id}已经是{state.status}"
    # 在这个地方修改的状态
    # 此处approve的值是哪来的？是队长的LLM决定要不要通过
    state.status = "approved" if approve else "rejected"
    # 如果队长给队友发了一个已拒绝的消息，队友或者重新生成一个并提交一份新的计划再次提交审批，或者就直接放弃了
    BUS.send(
        LEAD_NAME,  # 队长
        state.sender,  # 队友
        feedback or ("已批准" if approve else "已拒绝"),
        "plan_approval_response",  # 消息类型为计划审批的响应
        {"request_id": request_id, "approve": approve},
    )
    icon = "√" if approve else "×"
    print(f"\x1b[32m 协议 计划 {icon} {request_id} \x1b[0m")
    status_text = "已批准" if approve else "已拒绝"
    return f"计划{request_id}{status_text}"


# 等待队友的结果
def wait_for_teammates(names, timeout):
    """
    阻塞等待指定(就全部的pending队友)的队友的result
    等待期间轮询消费lead收件箱中的消息，最后返回汇总文本供tool_result使用
    """
    timeout = TEAMMATE_WAIT_TIMEOUT if timeout is None else timeout
    # 已经派发子线程 ，但是尚未收到这个子线程结果的agent的名称
    targets = set(names) if names else set(pending_teammate_results)
    if not targets:
        return f"没有待等待的队友result"
    targets &= pending_teammate_results
    if not targets:
        return f"指定队友的result均已经收到"
    print(
        f"\x1b[33m [屏障] 等待队友result:{','.join(sorted(targets))},超时时间为{timeout:.0f}s \x1b[0m"
    )
    # 等待的截止时间
    deadline = time.time() + timeout
    # 等待期间收集到的队友发过来的消息
    collected = []
    # 在2分钟以内不断检查收件箱
    while time.time() < deadline:
        # 检查收到收件箱里的消息列表
        inbox = consume_lead_inbox(route_protocol=True)
        # 如果收到了，就添加到collected里
        if inbox:
            collected.extend(inbox)
        # 收完这一轮消息后再判断一下是否还有剩下的等待结果的队友
        remaining = targets & pending_teammate_results
        # 如果已经没有在等待的队友了，则直接退出循环
        if not remaining:
            break
        # 如果这个时候这个队友其实已经因为意外线程死掉了，或者说退出了
        for n in list(remaining):
            if n in pending_teammate_results and not is_teammate_running(n):
                pending_teammate_results.discard(n)
                print(f"\x1b[33m {n}已经结束了，但也没有result,解除等待 \x1b[0m")
        time.sleep(WAIT_POLL_INTERVAL)

    # 还在等待结果的队友的名称
    remaining = sorted(targets & pending_teammate_results)
    # 如果等待2分钟后还有剩余，那么会把现状汇总结发给大模型，后续如何处理看大模型的决策
    parts = []
    if collected:
        parts.append(format_inbox_messages(collected))
    if remaining:
        parts.append(
            f"等待超时或未完成，仍然缺少result->{','.join(remaining)}"
            f"可再次await_teammates,或request_shutdown"
        )
    else:
        parts.append(f"已经收到全部result:{','.join(sorted(targets))}")
    #
    return "\n".join(parts)


def list_pending_teammates():
    return sorted(pending_teammate_results)


def apply_teammate_stop_barries(messages):
    """
    lead无tool_calls的准备STOP时调用
    如果此时仍有pending_result,阻塞等待-注入收件箱-返回应追加user提示
    无pending则返回None，允许真正退出
    """
    pending = list_pending_teammates()
    if not pending:
        n = inject_lead_inbox(messages)
        if n:
            return "队友屏障 退出前从收件箱注入到迟到的消息，请根据此更新回复后再结束"
        return None
    status = wait_for_teammates(names=pending, timeout=TEAMMATE_WAIT_TIMEOUT)
    inject_lead_inbox(messages)
    still = list_pending_teammates()
    hint = (
        f"队友屏障 {status}\n"
        "请根据收件箱中的队友结果汇总后回复用户"
        "不要在未看到result时声称任务已经完成"
    )
    if still:
        hint += f"\n仍在等待：{','.join(still)}"
    print(f"\x1b[33m Stop已经拦截，注入汇总后继续下一轮  \x1b[0m")
    return hint
