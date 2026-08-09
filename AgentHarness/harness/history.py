import json
import time
from config import (
    MAX_BYTES,
    PERSIST_THRESHOLD,
    TOOL_RESULTS_DIR,
    TEXT_ENCODING,
    MAX_MESSAGES_LENGTH,
    KEEP_RECENT,
    TRANSCRIPTS_DIR,
    client,
    MODEL_ID,
    DEFAULT_MAX_TOKENS,
)


def persist_large_output(tool_call_id: str, output: str):
    if len(output) < PERSIST_THRESHOLD:
        return output
    # 创建工具结果输出目录，如果已经存在则跳过，不存在则创建，如果父目录不存在，即递归创建父目录
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # 创建持久化的工具结果的路径
    path = TOOL_RESULTS_DIR / f"{tool_call_id}.txt"
    # 如果路径不存在
    if not path.exists():
        # 把工具结果的内容完整写入此路径
        path.write_text(output, encoding=TEXT_ENCODING)
    # 把结果落盘之后，会把此工具的落盘的路径放到上下文中，以后如果AI需要这个结果，会再次尝试读回来
    return f"<persisted_output>\n完整输出路径:{path}\n预览:\n{output[:PERSIST_THRESHOLD]}\n</persisted_output>"


# 0 API就是不调用任何的大模型API
# 定义函数，用于管理某些人类型的消息的总内容体积预算
def tool_result_budget(messages: list, max_bytes: int = MAX_BYTES):
    # 获取所有的role为tool的消息的下标索引列表
    indices = [
        index for index, message in enumerate(messages) if message.get("role") == "tool"
    ]
    # 如果没有tool类型的消息，直接返回原消息列表
    if not indices:
        return messages
    # 计算所有的tool消息内容的总字节数
    total = sum(len(str(messages[index].get("content", ""))) for index in indices)
    # 如果总字节数未超过最大限制，直接返回原来的消息列表
    if total < max_bytes:
        return messages
    # 按工具消息内容的长度大小对工具消息进行降序排列
    ranked = sorted(
        indices,
        key=lambda index: len(str(messages[index].get("content", ""))),
        reverse=True,
    )
    # 遍历排序后的工具消息下标
    for index in ranked:
        # 如果总字节数已经小于等于最大预算值了，停止处理
        if total <= max_bytes:
            break
        # 获取索引对应的消息
        msg = messages[index]
        # 获取消息的内容
        content = str(msg.get("content", ""))
        # 如果此消息的内容长度小于设置的持久化阈值的话，跳过不处理
        if len(content) <= PERSIST_THRESHOLD:
            continue
        # 获取工具调用的ID
        tool_id = msg.get("tool_call_id", "unknown")
        # 将大的输出内容持久化硬盘上，并替换为简短信息
        msg["content"] = persist_large_output(tool_id, content)
        # 再重新计算所有的tool消息长度的总和
        total = sum(len(str(messages[index].get("content", ""))) for index in indices)
    return messages


# 修复消息链，确保每个asssitant的tool_call都可以收到tool响应，同时移除孤立的tool消息
# 最终要保证tool_call和tool是一一对应的
def repair_message_chain(messages: list):
    if not messages:
        return messages
    # 用于保存修复后的消息列表
    repaired_messages = []
    # 记录等待tool响应的tool_call_id的集合
    pending_call_ids = set()

    # 将当前正在等待的tool call id用reason伪造tool消息并清空pending_call_ids集合
    def flush_pending(reason: str):
        nonlocal pending_call_ids
        # 遍历所有的等待补全的tool call id ,添加伪造tool消息响应
        for tool_call_id in pending_call_ids:
            repaired_messages.append(
                {"role": "tool", "tool_call_id": tool_call_id, "content": reason}
            )
        pending_call_ids = set()

    # 遍历消息列表
    for msg in messages:
        # 获取当前的消息对应的角色
        role = msg.get("role")
        # 如果这个消息是AI助手的话
        if role == "assistant":
            # 必须为之前等待的toolcallid自动补全工具响应
            flush_pending("[工具响应缺失，已自动补全]")
            repaired_messages.append(msg)
            # 获取本次AI消息里的工具调用请求
            tool_calls = msg.get("tool_calls") or []
            # 提取本次assistant消息关联的所有的tool调用ID
            pending_call_ids = {
                tool_call.get("id")
                for tool_call in tool_calls
                if isinstance(tool_call, dict) and tool_call.get("id")
            }
            continue
        elif role == "tool":
            tool_call_id = msg.get("tool_call_id")
            # 如果toolcallid有效，并且在待补全的ID集合中
            if tool_call_id and tool_call_id in pending_call_ids:
                # 添加此tool消息到修复后的结果中
                repaired_messages.append(msg)
                # 标记此ID已经完成，不再需要等待配对了，可以移除pending
                pending_call_ids.discard(tool_call_id)
            continue
        else:
            flush_pending("[工具响应缺失，已自动补全]")
            repaired_messages.append(msg)
    flush_pending("[工具响应缺失，已自动补全]")
    return repaired_messages


def snip_compact(messages: list, max_messages: int = MAX_MESSAGES_LENGTH):
    # 如果当前的消息总数未超过最大限制，则直接返回
    if len(messages) <= max_messages:
        return messages
    # 指定头部和尾部分别保留的消息数量
    keep_head, keep_tail = 3, max_messages - 3
    # 计算即将被裁剪的消息条数
    snipped = len(messages) - keep_head - keep_tail
    # 构建裁剪后的消息列表 头+说明消息+尾部
    compacted_messages = (
        messages[:keep_head]  # 头部3条 :3
        + [{"role": "user", "content": f"[已裁剪{snipped}条消息]"}]  # 一条说明性的消息
        + messages[-keep_tail:]  # 尾部 -47:
    )
    return repair_message_chain(compacted_messages)


def collect_tool_messages(messages: list):
    # 遍历消息列表，筛选出角色为tool的消息，并返回对应的索引和消息本身组成的元组列表
    return [
        (index, msg) for index, msg in enumerate(messages) if msg.get("role") == "tool"
    ]


def micro_compact(messages: list):
    # 收集所有的tool类型的消息及索引tool_msgs 10
    tool_msgs = collect_tool_messages(messages)
    # 如果tool的消息数量不超过设定的保留数量，直接返回原来的消息列表
    if len(tool_msgs) <= KEEP_RECENT:  # 3
        return messages
    # 遍历除最近保留的设定的保留数以外的其它工具消息   tool_msgs[0:-3] tool_msgs[0:7]
    for index, msg in tool_msgs[:-KEEP_RECENT]:
        content = str(msg.get("content", ""))
        # 如果内容的长度大于120，则要进行压缩
        if len(content) > 120:
            msg["content"] = "[较早的工具结果已经压缩，需要时重新运行]"
    return messages


# 计算消息列表字符串长度
def estimate_size(messages: list):
    return len(str(messages))


def write_transcript(messages: list):
    # 创建转录目录
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    # 拼接生成的转录文件的路径
    path = TRANSCRIPTS_DIR / f"transcript_{int(time.time())}.jsonl"
    with path.open("w", encoding=TEXT_ENCODING) as f:
        for msg in messages:
            # 将每条消息转为json字符串并写入文件，每条一行
            f.write(json.dumps(msg, default=str, ensure_ascii=False) + "\n")
    return path


def summarize_history(messages: list):
    # 将消息列表转换为json字符串，并裁剪至8万个字符
    conversation = json.dumps(messages, default=str, ensure_ascii=False)[:80000]
    prompt = (
        "总结以下Agent对话，以便继续工作\n"
        "保留1. 当前目标 2.关键发现、决策 3.读和改过的文件 4.剩余工作 5.用户约束 \n简洁但具体。\n\n"
        + conversation
    )
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=DEFAULT_MAX_TOKENS,
    )
    return (response.choices[0].message.content or "").strip() or "(空摘要)"


def compact_history(messages: list):
    transcript_path = write_transcript(messages)
    print(f"[转录已经保存]:{transcript_path}")
    # 对历史消息进行摘要压缩
    summary = summarize_history(messages)
    # 返回仅仅包含摘要的文本消息列表(角色为用户)
    return [{"role": "user", "content": f"[已压缩]\n\n{summary}"}]


def reactive_compact(messages: list):
    write_transcript(messages)
    summary = summarize_history(messages)
    # 生成一个压缩后的消息链(包括用户摘要加上最近的5条消息，并进行修正处理)
    # 保留消息列表中最后的5条消息
    return repair_message_chain(
        [{"role": "user", "content": f"[响应式压缩]\n\n{summary}"}, *messages[-5:]]
    )
