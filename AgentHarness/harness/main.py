from agent import agent_loop
from hooks import trigger_user_prompt_hooks
from cron import start_cron_scheduler, start_queue_processor
import threading
import argparse
from session import save_session, session_exists, load_session, format_session_summary
from config import SESSION_LATEST
from rich import print

# 定义互斥锁用于线程同步
agent_lock = threading.Lock()

# 定义会话历史消息列表 这个消息列表只供主Agent使用，队友不会用的
session_history = []


# 定义函数，带锁执行agentLoop,可选参数为用户的输入
def run_agent_turn_locked(query: str | None = None):
    if query:
        # 将用户的输入添加到历史列表中
        session_history.append({"role": "user", "content": query})
    # 调用代理循环处理历史消息
    agent_loop(session_history)
    # 获取历史记录中最后一条消息
    final = session_history[-1]
    # 如果最后一条消息是助手回复，并且有内容输出则输出该内容
    if final.get("role") == "assistant" and final.get("content"):
        print(final["content"])


def _parse_args():
    parser = argparse.ArgumentParser(description="Agent Harness CLI")
    parser.add_argument(
        "--resume",
        action="store_true",
        help=f"从{SESSION_LATEST}恢复上次的会话并继续聊天",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    # 如果指定此参数，说明 要恢复 上次的会话
    if args.resume:
        if session_exists():
            restored = load_session()
            session_history.clear()
            session_history.extend(restored)
            print(
                f"\x1b[36m  会话已经恢复:{format_session_summary(session_history)} \x1b[0m"
            )
        else:
            print(f"\x1b[36m  未找到{SESSION_LATEST}文件，从空对话开始吧 \x1b[0m")
    print(session_history)
    # 定时投递安排任务产生任务 作用是启动定时任务调度器，负责定时周期性的向任务队列投递任务
    start_cron_scheduler()
    # 消息/处理任务队列中的实际任务，作用是不断轮询检查任务队列，一旦有待处理的任务，就会调用agent处理方法来完成任务
    start_queue_processor(run_agent_turn_locked, agent_lock)
    print("输入问题，回车发送。输入q 退出。\n")
    if args.resume and session_history:
        print("已经恢复了上次的会话，输入问题继续，回车发送，输入q退出\n")
    else:
        print("输入问题，回车发送，输入q退出\n")
        print(f"下次可以用--resume从{SESSION_LATEST.name}接着聊")
    # 进入无限循环，不断接收用户的输入
    while True:
        try:
            # 获取用户输入，带有提示符
            query = input("\x1b[36m>> \x1b[0m")
        except (EOFError, KeyboardInterrupt):
            # 异常时输出循环
            break
        # 如果本次输入的值为空，就继续下一轮
        if not query.strip():
            continue
        # 如果输入的内容为空，或者用户输入了q quit exit 空串 都退出循环
        if query.strip().lower() in ("q", "quit", "exit"):
            with agent_lock:
                if session_history:
                    save_session(session_history)
                print(
                    f"\x1b[90m 会话退出前已经保存 {len(session_history)}条对话记录 \x1b[0m"
                )
            break
        # 触发'UserPromptSubmit'钩子，进行前置处理，返回处理后的用户输入
        query = trigger_user_prompt_hooks(query)
        with agent_lock:
            run_agent_turn_locked(query)


if __name__ == "__main__":
    main()
