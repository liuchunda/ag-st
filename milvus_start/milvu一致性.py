# 选项
# 在Milvus数据库创建集合时，有四种一致性选项

# 5.4.1.1.Strong（强一致性）
# 比如在班级里，当老师发布一条通知后，所有同学必须立即收到并确认，老师才会继续下一步。这种方式最可靠，但速度较慢，因为要等待每个人都确认。

# 5.4.1.2.Session（会话一致性）
# 这像是你和好友的私聊。你发的消息，你的好友一定能按顺序收到，但其他同学可能暂时看不到或顺序不同。

# 5.4.1.3.Bounded（有界一致性）
# 这像是黑板上写的通知。老师写完通知后，同学们会在一定时间内（比如10分钟）都能看到，但不要求立即。

# 5.4.1.4.Eventually（最终一致性）
# 这像是口口相传的小道八卦消息。信息最终会传到每个人那里，但可能需要较长时间，且不保证具体何时。


# 如何选择？
# 需要数据绝对准确时（如银行交易）→ 选Strong
# 需要用户看到自己操作的结果时 → 选Session
# 需要在一定时间内保证一致性 → 选Bounded
# 对时间要求不高，但希望系统运行更快 → 选Eventually

import random
import time
from typing import List, Dict

STUDENTS = ["小张", "小李", "小王", "小刘"]


def strong_consistency(message: str) -> None:
    """说明：强一致性——必须等所有人确认收到后，老师才算广播成功。"""
    print("\n[Strong] 老师开始广播：", message)
    for name in STUDENTS:
        print(f"  → {name} 收到并确认：{message}")
        time.sleep(0.3)  # 模拟等待确认
    print("[Strong] 所有人都确认，老师继续下一步\n")


def session_consistency(message: str, session_owner: str) -> None:
    """说明：会话一致性——只保证当前会话（某个学生）看到自己的操作，其他同学稍后再同步。"""
    print(f"\n[Session] {session_owner} 在私聊中提交：{message}")
    print(f"  → {session_owner} 立即看到自己发的内容")
    print("  → 其他同学稍后通过公共同步获得，不保证时间顺序\n")


def bounded_consistency(message: str, bound_seconds: int = 5) -> None:
    """说明：有界一致性——在指定时间窗口内同步即可，不要求立刻。"""
    print(f"\n[Bounded] 老师写在黑板上：{message}（需要在 {bound_seconds} 秒内传达到）")
    reached: Dict[str, float] = {}
    for name in STUDENTS:
        delay = random.uniform(0, bound_seconds)
        time.sleep(delay / 10)  # 缩短真实等待，方便演示
        reached[name] = delay
        print(f"  → {name} 在 {delay:.2f} 秒后看到黑板信息")
    print("[Bounded] 所有人都在规定时间内看到了通知\n")


def eventual_consistency(message: str) -> None:
    """说明：最终一致性——通知顺序与到达时间都不确定，但最终所有人会知道。"""
    print("\n[Eventually] 消息通过口口相传传播：", message)
    remaining = STUDENTS.copy()
    random.shuffle(remaining)
    total_delay = 0.0
    while remaining:
        name = remaining.pop()
        delay = random.uniform(0.5, 2.0)
        total_delay += delay
        time.sleep(delay / 10)  # 缩短等待
        print(f"  → {name} 在约 {total_delay:.1f} 秒后才听到消息")
    print("[Eventually] 虽然有延迟，但最终每个人都掌握了消息\n")


if __name__ == "__main__":
    strong_consistency("今晚 8 点线上作业答疑")
    session_consistency("我提交了一次向量插入操作", session_owner="小李")
    bounded_consistency("10 分钟内完成实验截图上交", bound_seconds=10)
    eventual_consistency("下周可能有一次临时测验，注意关注群通知")