from config import (
    client,
    MODEL_ID,
    MAX_RETRIES,
    BASE_DELAY_MS,
    MAX_CONSECUTIVE_529,
    FALLBACK_MODEL_ID,
    DEFAULT_MAX_TOKENS,
)
from tools.schema import TOOLS
from openai import APIStatusError, RateLimitError
import random
import json
import time


# 定义调用大模型的函数
# system 系统提示词 messages消息列表，里面现在只有用户消息 max_tokens最大token数 model模型名称
def call_llm(system: str, messages: list, max_tokens: int, model: str, tools=None):
    return client.chat.completions.create(
        model=model,
        # 将系统提示消息和原来的消息列表组成messages
        messages=[{"role": "system", "content": system}, *messages],
        tools=tools if tools is not None else TOOLS,  # type: ignore
        max_tokens=max_tokens,
    )


def is_prompt_too_long_error(e: Exception):
    msg = str(e).lower()
    return (
        ("prompt" in msg and "long" in msg)
        or "prompt_is_too_long" in msg
        or "context_length_exceeded" in msg
        or "max_context_window" in msg
        or "contxt_length" in msg
        or "maximum content" in msg
    )


# 定义一个类，用来表示恢复的状态
class RecoveryState:
    def __init__(self) -> None:
        # 表示是否已经尝试过升级变大max_tokens
        self.has_escalated = False
        # 当前正在使用的模型
        self.current_model = MODEL_ID
        self.max_tokens = DEFAULT_MAX_TOKENS
        # 连续发生529错误的次数
        self.consecutive_529 = 0
        # 是否已经尝试过被动压缩
        self.has_attempted_reactive_compact = False
        # 恢复尝试的次数计数器
        self.recovery_count = 0


def _is_rate_limit_error(e: Exception):
    if isinstance(e, RateLimitError):
        return True
    # 错误消息
    msg = str(e).lower()
    # 类的名称
    name = type(e).__name__.lower()
    # 如果类名里包括ratelimit。或者错误消息中包括429的话就是速率错误
    return "ratelimit" in name or "429" in msg


def _is_overloaded_error(e: Exception):
    if isinstance(e, APIStatusError) and getattr(e, "status_code", None) == 529:
        return True
    # 错误消息
    msg = str(e).lower()
    # 类的名称
    name = type(e).__name__.lower()
    return "overloaded" in name or "overloaded" in msg or "529" in msg


# 计算重试的延迟时间
def retry_delay(attempt: int, retry_after=None):
    # 如果指定多长时间后重试，直接转为浮点数返回
    if retry_after:
        try:
            return float(retry_after)
        except (TypeError, ValueError):
            pass
    base = min(BASE_DELAY_MS * 2**attempt, 32000) / 1000
    return base + random.uniform(0, base * 0.25)


# 为一个函数增加重试的机制
def with_retry(fn, state: RecoveryState):
    # 尝试MAX_RETRIES次
    for attempt in range(MAX_RETRIES):
        try:
            result = fn()
            return result
        # 捕获所有的异常
        except Exception as e:
            # 把错误进行分类处理，如果遇到的是速率限制错误
            if _is_rate_limit_error(e):
                # 计算重试等待时间
                delay = retry_delay(attempt)
                print(f"[速率限制] 重试{attempt+1}/{MAX_RETRIES}，等待{delay:1f}")
                # 等待delay秒
                time.sleep(delay)
                # 继续循环
                continue
            if _is_overloaded_error(e):
                # 如果遇到的是529，也就是服务器端过载的话
                state.consecutive_529 += 1
                # 如果连续发生529的次数大于等于阈值的话
                if state.consecutive_529 >= MAX_CONSECUTIVE_529:
                    if FALLBACK_MODEL_ID and state.current_model != FALLBACK_MODEL_ID:
                        state.current_model = FALLBACK_MODEL_ID
                        state.consecutive_529 = 0
                        print(f"切换到备用模型{FALLBACK_MODEL_ID}")
                    elif not FALLBACK_MODEL_ID:
                        state.consecutive_529 = 0
                        print("未配置备用模型，请继续重试")
                    else:
                        state.consecutive_529 = 0
                delay = retry_delay(attempt)
                time.sleep(delay)
                continue
            # 非速率/过载错误：直接抛出，避免把 401 等误当成 529 反复重试
            raise
    raise RuntimeError(f"超过了最大重试次数({MAX_RETRIES})")
