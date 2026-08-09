import json
from config import (
    DEFAULT_MAX_TOKENS,
    MODEL_ID,
    CONTEXT_LIMIT,
    TODO_REMINDER_ROUNDS,
    ESCALATE_MAX_TOKENS,
    MAX_RECOVERY_RETRIES,
    CONTINUATION_PROMPT,
    TEAMMATE_BARRIER_ROUNDS,
)
from prompt import get_system_prompt
from llm import call_llm, is_prompt_too_long_error, RecoveryState, with_retry
from utils import assistant_message_dict, message_text
from tools.executor import execute_tool
from hooks import trigger_hooks
from history import (
    tool_result_budget,
    snip_compact,
    micro_compact,
    estimate_size,
    repair_message_chain,
    compact_history,
    reactive_compact,
)
from memory import load_memories, extract_memories, consolidate_memories
from tools.handlers import todo_update_reminder
from background import (
    should_run_background,
    start_background_task,
    collect_background_results,
)
from cron import consume_cron_queue
from teams import inject_lead_inbox, apply_teammate_stop_barries
from mcp import assemble_tool_pool, connected_mcp_summary

# 定义变量,用于记录上次todo_write调用以来的轮数
rounds_since_todo = 0


def agent_loop(messages: list):
    # 创建一个记录恢复状态的实例
    state = RecoveryState()
    # 本回合已经触发的队友收尾屏障次数(防止无限拦截STOP)
    barrier_rounds = 0
    # 声明这是全局变量
    global rounds_since_todo
    while True:
        tools, handlers = assemble_tool_pool()
        # 调用consume_cron_queue方法，获取需要执行的定时任务，并赋值给fired
        fired = consume_cron_queue()
        # 遍历所有的被触发的定时任务
        for job in fired:
            messages.append({"role": "user", "content": f"[执行定时任务] {job.prompt}"})
            print(f"\x1b[33m [注入Cron计划任务] {job.prompt}\x1b[0m")
        # 把主管收件箱的消息注入到消息列表中，让主Agent大模型能看到别的队友给他发的消息
        inject_lead_inbox(messages)
        # 从后台收集通知，如果有的话
        bg_notification = collect_background_results()
        if bg_notification:  # system assisstant tool user
            messages.append({"role": "user", "content": "\n\n".join(bg_notification)})
            print(f"[注入]{len(bg_notification)}条后台结果通知到消息列表中")
        # 获取系统提示词
        system = get_system_prompt()
        mcp_summary = connected_mcp_summary()
        if mcp_summary:
            system += "\n\n" + mcp_summary
        # 加载有关历史消息的记忆内容
        memories_content = load_memories(messages)
        # 如果记内容是存在的
        if memories_content:
            # 将记忆内容追加到系统提示词后面
            system += "\n\n" + memories_content
        # 如果有活跃的TODO且N轮未更新的话，把提醒消息写入system
        todo_remainder = todo_update_reminder(rounds_since_todo, TODO_REMINDER_ROUNDS)
        if todo_remainder:
            system += "\n\n" + todo_remainder
            print(f"\x1b[33m][todo提醒] 连续{rounds_since_todo}轮未更新\x1b[0m]")

        # 创建一个用于提取记忆的消息内容列表
        pre_compress = [
            {"role": m.get("role", ""), "content": message_text(m)}
            for m in messages
            if isinstance(m, dict)
        ]
        # L3:tool_result_budget  超大tool结果落盘
        messages[:] = tool_result_budget(messages)
        # L1 snip_compact 消息>50条的时候保留头3+尾47 ，中间裁掉
        messages[:] = snip_compact(messages)
        # L2: micro_compact — 旧工具结果占位 仅保留最近3条tool的完整内容，旧的变成占位符
        messages[:] = micro_compact(messages)
        # L4: compact_history — LLM 全量摘要
        if estimate_size(messages) > CONTEXT_LIMIT:
            messages[:] = compact_history(messages)
        messages[:] = repair_message_chain(messages)
        try:
            # 调用大模型获取回复
            response = with_retry(
                lambda: call_llm(
                    system, messages, state.max_tokens, state.current_model, tools=tools
                ),
                state,
            )
        except Exception as e:
            # 如果报的错误是提示词过长的导致的错误
            if is_prompt_too_long_error(e):
                # 如果还没有尝试过被动压缩
                if not state.has_attempted_reactive_compact:
                    # 对消息列表进行反应式压缩，减少消息长度
                    messages[:] = reactive_compact(messages)
                    state.has_attempted_reactive_compact = True
                    continue
                # 如果已经尝试过了，还是报这个错
                print(f"[不可恢复] 已经尝试过被动压缩，但还是太长")
                messages.append(
                    {"role": "assistant", "content": "[错误]上下文太长，无法继续"}
                )
                return
            name = type(e).__name__
            print(f"[不可恢复] {name} {str(e)[:100]}")
            messages.append(
                {"role": "assistant", "content": f"[错误]{name}:{str(e)[:100]}"}
            )
            return

        # 获取助手返回的消息
        choice = response.choices[0]  # type: ignore
        # 判断回复是否是因为达到最大限度被 截断
        if choice.finish_reason == "length":
            # 如果尚未升级max_tokens
            if not state.has_escalated:
                state.max_tokens = ESCALATE_MAX_TOKENS
                state.has_escalated = True
                print(f"[max_tokens] {DEFAULT_MAX_TOKENS}升级到{ESCALATE_MAX_TOKENS}")
                continue
            # 把助手消息以字典的形式添加到消息列表中
            messages.append(assistant_message_dict(choice.message))
            # 如果本次回复需要调用工具的话
            if choice.message.tool_calls:
                # 虽然不能调用工具了，但为了保证工具消息合法性，还是需要给工具调用配齐调用结果
                for tool_call in choice.message.tool_calls:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": "[输出被截断，未能执行工具]",
                        }
                    )
                # 跳出本次循环，重新开始
                continue
            # 如果还在允许 的最大恢复 次数范围内
            if state.recovery_count < MAX_RECOVERY_RETRIES:
                messages.append({"role": "user", "content": CONTINUATION_PROMPT})
                state.recovery_count += 1
                print(f"续写{ state.recovery_count}/{MAX_RECOVERY_RETRIES}")
                continue
            print("已经达到了恢复上限")
            return

        assistant = choice.message
        # 消耗的token在choice.usage
        # 将助手的回复以字典的形式添加到消息列表
        messages.append(assistant_message_dict(assistant))
        # 每一轮调用让计数器加1
        rounds_since_todo += 1
        # 如果助手没有工具调用，则终止循环
        if not assistant.tool_calls:
            if barrier_rounds < TEAMMATE_BARRIER_ROUNDS:
                barrier_msg = apply_teammate_stop_barries(messages)
                if barrier_msg:
                    barrier_rounds += 1
                    messages.append({"role": "user", "content": barrier_msg})
                    continue
            # 提取记忆
            extract_memories(pre_compress)
            # 合并或者说整理记忆
            consolidate_memories()
            # 调用trigger_hooks函数，触发名为Stop的钩子，传入当前的消息列表
            force = trigger_hooks("Stop", messages)
            # 如果force有值说明活没干完，也就是hook返回了需要进一步处理的信息
            if force:
                # 如果有值，则将其作为用户角色的消息添加到消息列表中
                messages.append({"role": "user", "content": force})
                # 继续while循环，重新进入 agent loop的流程
                continue
            return
        # 如果助手要调用某些人，则循环所有的工具调用
        for tool_call in assistant.tool_calls:
            # 获取工具名称
            name = tool_call.function.name  # type: ignore
            # 获取解析工具参数
            args = json.loads(tool_call.function.arguments or "{}")  # type: ignore
            # 如果用户想调的工具是压缩工具的话
            if name == "compact":
                messages[:] = compact_history(messages)
                # 跳出当前的for 循环进入下一轮的while循环
                break
            # 触发PreToolUse这个钩子，判断是否允许工具执行
            blocked = trigger_hooks("PreToolUse", name, args)
            # 只要有一个钩子函数返回一个非None的值，后面的钩子就不走了，
            if blocked:
                # 将阻止信息以tool角色的形式添加到消息列表中
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(blocked),
                    }
                )
                continue
            # 判断是否应该以后台任务运行工具
            if should_run_background(name, args):
                # 启动后台任务，并获取后台任务ID
                bg_id = start_background_task(tool_call.id, name, args)
                output = (  # Return Placeholder
                    f"后台任务[{bg_id}]已经启动"
                    f"命令:{args.get('command','')}"
                    f"完成后将通过task_notification通知"
                )
            else:
                output = execute_tool(name, args, handlers=handlers)
            # 触发PostToolUse钩子，并进行后置处理
            trigger_hooks("PostToolUse", name, args, output)
            # 如果本次调用的工具就是todo_write,则也重置轮数计数器为0
            # 如果使用connect_mcp工具连接了新的服务器以后，要重建工具池，以便下一轮使用
            if name == "connect_mcp":
                tools, handlers = assemble_tool_pool()
            if name == "todo_write":
                rounds_since_todo = 0
            # 把工具调用的结果以特定的工具格式添加到消息列表
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": output}
            )
