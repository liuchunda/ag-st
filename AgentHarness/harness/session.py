import time
import json
from config import SESSION_DIR, SESSION_LATEST, TEXT_ENCODING

SESSION_VERSION = 1


def _ensure_session_dir():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def save_session(messages, path=None):
    _ensure_session_dir()
    target = path or SESSION_LATEST
    payload = {
        "version": SESSION_VERSION,
        "updated_at": time.time(),
        "message_count": len(messages),
        "messages": messages,
    }
    # 先写临时文件，再替换，避免进程中断留下半截JSON
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=True, default=str, indent=2),
        encoding=TEXT_ENCODING,
    )
    tmp.replace(target)
    return target


def session_exists(path=None):
    return (path or SESSION_LATEST).exists()


def load_session(path=None):
    target = path or SESSION_LATEST
    if not target.exists():
        return []
    data = json.loads(target.read_text(encoding=TEXT_ENCODING))
    messages = data.get("messages")
    return messages


def format_session_summary(messages):
    if not messages:
        return "(空会话)"
    roles = {}
    for m in messages:
        if isinstance(m, dict):
            r = m.get("role", "?")
            roles[r] = roles.get("r", 0) + 1
    parts = [f"{k}={v}" for k, v in sorted(roles.items())]
    return f"有{len(messages)}条消息，{','.join(parts)}"
