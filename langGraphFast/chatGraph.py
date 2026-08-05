from pathlib import Path
from pprint import pprint
from typing import Annotated, Any

from typing_extensions import NotRequired, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import InjectedState, ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from langchain.chat_models import init_chat_model
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_tavily import TavilySearch

from config.ai_configs import ai_configs
from config.env import env

# thread_id 只有配合 checkpointer 才有多轮记忆
config = {"configurable": {"thread_id": "123"}}
memory = InMemorySaver()


class State(TypedDict):
    # messages 的类型是 list。注解里的 `add_messages` 定义了该状态字段如何更新
    messages: Annotated[list, add_messages]
    # list_directory 通过 Command(update=...) 写入
    last_listed_path: NotRequired[str | None]
    last_listing: NotRequired[str | None]
    list_approved: NotRequired[bool]
    # 已人工同意过的绝对路径；再次查看同路径时跳过 interrupt
    approved_paths: NotRequired[list[str]]
    # time_travel 工具写入；本轮结束后由外层按该检查点重放
    pending_replay_checkpoint_id: NotRequired[str | None]


def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    human_response = interrupt({"query": query})
    return human_response["data"]


def _build_listing(target: Path) -> str:
    if not target.exists():
        return f"路径不存在: {target}"
    if not target.is_dir():
        return f"不是目录: {target}"
    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    if not entries:
        return f"{target} 是空目录"
    lines = [f"{'[DIR] ' if p.is_dir() else '[FILE]'} {p.name}" for p in entries]
    return f"{target}\n" + "\n".join(lines)


@tool
def list_directory(
    path: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """列出电脑上某个本地路径下的文件和子目录。
    当用户要查看目录、列文件、ls、看某个文件夹内容时使用。
    首次访问某路径会暂停并请求人工同意；同路径已批准过则不再询问。
    成功后会把路径和列表写入 state。
    """
    target = Path(path).expanduser().resolve()
    target_key = str(target)
    approved_paths = list(state.get("approved_paths") or [])
    already_approved = target_key in approved_paths or (
        bool(state.get("list_approved"))
        and state.get("last_listed_path") == target_key
    )

    if not already_approved:
        decision = interrupt(
            {
                "action": "list_directory",
                "path": path,
                "message": f"是否允许查看目录「{path}」？请输入 yes 同意 / no 拒绝",
            }
        )
        approved = (
            decision is True
            or str(decision).strip().lower() in {"yes", "y", "true", "同意", "ok"}
        )
        if not approved:
            response = f"用户拒绝查看目录: {path}"
            return Command(
                update={
                    "list_approved": False,
                    "last_listed_path": target_key,
                    "last_listing": None,
                    "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
                }
            )

    response = _build_listing(target)
    new_approved_paths = (
        approved_paths
        if target_key in approved_paths
        else approved_paths + [target_key]
    )
    return Command(
        update={
            "list_approved": True,
            "last_listed_path": target_key,
            "last_listing": response,
            "approved_paths": new_approved_paths,
            "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
        }
    )


def _find_checkpoint_for_travel(target: str):
    """按 checkpoint_id / step / 消息关键词查找检查点；优先选 next 非空的，便于真正重放。"""
    history = list(graph.get_state_history(config))
    target = target.strip()
    if not target:
        return None

    for state in history:
        cid = state.config.get("configurable", {}).get("checkpoint_id", "")
        if cid == target or (len(target) >= 8 and cid.startswith(target)):
            return state

    step_str = target.lower().removeprefix("step").strip().strip("=").strip()
    if step_str.lstrip("-").isdigit():
        step = int(step_str)
        for state in history:
            if (state.metadata or {}).get("step") == step:
                return state

    def _is_travel_request(text: str) -> bool:
        return any(k in text for k in ("穿梭", "时间旅行", "回溯", "重放"))

    exact: list[Any] = []
    fuzzy: list[Any] = []
    for state in history:
        for msg in state.values.get("messages") or []:
            if getattr(msg, "type", None) not in {"human", "user"}:
                continue
            content = getattr(msg, "content", "") or ""
            if not isinstance(content, str) or _is_travel_request(content):
                continue
            text = content.strip()
            if text == target:
                exact.append(state)
                break
            if target in text:
                fuzzy.append(state)
                break

    for group in (exact, fuzzy):
        for state in group:
            if state.next:
                return state
        if group:
            return group[0]
    return None


@tool
def time_travel(
    target: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """将对话时间旅行（回溯）到之前某个检查点，并从该点重新往下执行。
    当用户说「穿梭」「回溯」「回到之前」「时间旅行」「重放」时使用。
    target 可以是：checkpoint_id、step 数字（如 3 / step=3）、或当时的用户原话关键词（如「我是谁」）。
    """
    state = _find_checkpoint_for_travel(target)
    if state is None:
        response = (
            f"未找到与「{target}」匹配的检查点。"
            "请换用 step 数字、checkpoint_id，或更具体的历史消息关键词。"
        )
        return Command(
            update={
                "pending_replay_checkpoint_id": None,
                "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
            }
        )

    checkpoint_id = state.config["configurable"]["checkpoint_id"]
    step = (state.metadata or {}).get("step")
    next_nodes = list(state.next) if state.next else []
    n_msgs = len(state.values.get("messages") or [])
    if not next_nodes:
        response = (
            f"已定位检查点 step={step}, checkpoint_id={checkpoint_id}, "
            f"消息数={n_msgs}，但 next 为空（该点已结束），重放不会继续执行。"
            "请改选 next 含 chatbot/tools 的检查点（例如用户刚说完、助手尚未回复的那一步）。"
        )
        return Command(
            update={
                "pending_replay_checkpoint_id": None,
                "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
            }
        )

    response = (
        f"已定位检查点：step={step}, next={next_nodes}, "
        f"消息数={n_msgs}, checkpoint_id={checkpoint_id}。"
        "本轮结束后将从该点重新执行。"
    )
    return Command(
        update={
            "pending_replay_checkpoint_id": checkpoint_id,
            "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
        }
    )


search_tool = TavilySearch(
    max_results=2,
    tavily_api_key=env.tavily_api_key.strip(),
)
tools = [search_tool, human_assistance, list_directory, time_travel]

cfg = ai_configs["bailian-qwen3.6-plus"]
# ChatOpenAI / init_chat_model 的 base_url 不需要 /chat/completions 后缀
base_url = cfg["url"].removesuffix("/chat/completions")
# qwen thinking 模式不稳定支持 tools，先关掉
model = init_chat_model(
    cfg["model"],
    model_provider="openai",
    api_key=env.llm_key_bailian.strip(),
    base_url=base_url,
    temperature=0,
    extra_body={"enable_thinking": False},
)
llm_with_tools = model.bind_tools(tools)


graph_builder = StateGraph(State)


def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

graph = graph_builder.compile(checkpointer=memory)


def _print_assistant_from_event(event: dict) -> None:
    for value in event.values():
        if not isinstance(value, dict) or "messages" not in value:
            continue
        msg = value["messages"][-1]
        if getattr(msg, "content", None):
            print("Assistant:", msg.content)


def stream_graph(input_data: Any, run_config: dict | None = None) -> Any | None:
    """跑图；若触发 interrupt，返回 interrupt 的 value，否则返回 None。"""
    interrupt_value = None
    active_config = run_config or config
    for event in graph.stream(input_data, config=active_config, stream_mode="updates"):
        if "__interrupt__" in event:
            interrupt_value = event["__interrupt__"][0].value
            continue
        _print_assistant_from_event(event)
    png_bytes = graph.get_graph().draw_mermaid_png()
    out = Path(__file__).with_name("graph.png")
    out.write_bytes(png_bytes)
    print(f"流程图已保存: {out}")
    return interrupt_value


def maybe_replay_from_pending() -> None:
    """若 time_travel 工具写入了 pending_replay_checkpoint_id，则从该检查点重放。"""
    latest = graph.get_state(config)
    checkpoint_id = (latest.values or {}).get("pending_replay_checkpoint_id")
    if not checkpoint_id:
        return

    replay_state = None
    for state in graph.get_state_history(config):
        if state.config.get("configurable", {}).get("checkpoint_id") == checkpoint_id:
            replay_state = state
            break

    # 清掉标记，避免重复触发
    graph.update_state(config, {"pending_replay_checkpoint_id": None})
    if replay_state is None:
        print(f"时间旅行失败：找不到 checkpoint_id={checkpoint_id}")
        return

    print(
        f"===== 时间旅行重放：checkpoint_id={checkpoint_id}, "
        f"next={list(replay_state.next) if replay_state.next else []} ====="
    )
    pending = stream_graph(None, replay_state.config)
    while pending is not None:
        print("需要人工确认:", pending)
        answer = input("Human> ").strip()
        if isinstance(pending, dict) and pending.get("action") != "list_directory":
            resume_value = {"data": answer}
        else:
            resume_value = answer
        pending = stream_graph(Command(resume=resume_value))


def print_listing_state() -> None:
    values = graph.get_state(config).values
    print(
        "State 目录字段:",
        {
            "list_approved": values.get("list_approved"),
            "last_listed_path": values.get("last_listed_path"),
            "approved_paths": values.get("approved_paths"),
            "last_listing": values.get("last_listing"),
        },
    )


def _map_message(msg: Any) -> dict[str, Any]:
    role = getattr(msg, "type", None) or getattr(msg, "role", None) or "unknown"
    content = getattr(msg, "content", "") or ""
    if not isinstance(content, str):
        content = str(content)
    if len(content) > 200:
        content = content[:200] + "…"
    item: dict[str, Any] = {"role": role, "content": content}
    tool_calls = getattr(msg, "tool_calls", None) or []
    if tool_calls:
        item["tool_calls"] = [
            {
                "name": tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None),
                "args": tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", None),
            }
            for tc in tool_calls
        ]
    name = getattr(msg, "name", None)
    if name:
        item["name"] = name
    return item


def _map_history_item(state: Any) -> dict[str, Any]:
    values = state.values or {}
    return {
        "checkpoint_id": state.config.get("configurable", {}).get("checkpoint_id"),
        "next": list(state.next) if state.next else [],
        "step": (state.metadata or {}).get("step"),
        "created_at": state.created_at,
        "messages": [_map_message(m) for m in (values.get("messages") or [])],
        "list_approved": values.get("list_approved"),
        "last_listed_path": values.get("last_listed_path"),
        "approved_paths": values.get("approved_paths"),
    }


def print_state_history() -> None:
    history = [_map_history_item(s) for s in graph.get_state_history(config)]
    print(f"===== state history（共 {len(history)} 个，新 → 旧）=====")
    pprint(history, sort_dicts=False)


def handle_turn(user_input: str) -> None:
    pending = stream_graph({"messages": [{"role": "user", "content": user_input}]})
    # 可能连续 interrupt（少见）；一般一次审批后继续
    while pending is not None:
        print("需要人工确认:", pending)
        answer = input("Human> ").strip()
        # human_assistance 期望 resume 为 {"data": "..."}
        if isinstance(pending, dict) and pending.get("action") != "list_directory":
            resume_value = {"data": answer}
        else:
            resume_value = answer
        pending = stream_graph(Command(resume=resume_value))
    maybe_replay_from_pending()
    # 整轮跑完（含无 interrupt 的普通回答）再打印
    print_listing_state()
    print_state_history()


while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        handle_turn(user_input)
    except EOFError:
        break
