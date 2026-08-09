from pathlib import Path
from config import WORKDIR


# 工具函数，可以把pydantic类型的大模型回复消息对象转成字典
def assistant_message_dict(message) -> dict:
    # 使用model_dump可以把对象转字典，排除值为None的项
    data = message.model_dump(exclude_none=True)
    # 把角色的类型设置为助手
    data["role"] = "assistant"
    return data


# 参数为data(字节类型或None)返回一个字符串
def decode_subprocess_output(data: bytes | None) -> str:
    if not data:
        return ""
    for encoding in ("utf-8", "gbk", "cp936"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


# 此函数接收一个路径，返回一个Path
def safe_path(p: str, cwd: Path | None = None) -> Path:
    # 指定基础目录
    base = cwd or WORKDIR
    # 通过WORKDIR与p拼接，并调用resolve方法，得到p的绝对路径
    path = (base / p).resolve()
    # 判断path是不是在WORKDIR工作区内的子路径，如果不是则抛异常
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f"超出工作区:{p}")
    # 返回最终安全生成的路径对象
    return path


def extract_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def parse_frontmatter(text: str):
    # 如果文本不是以---开头，则直接返回空字典和原始文件
    if not text.startswith("---"):
        return {}, text
    # 用---分割文本，最多分割2次，得到3段内容
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    # 创建一个空字典，用于存储frontmatter键值对
    meta = {}
    # frontmatter 指是SKILL.md开头的YAML元数据块，用---包裹
    # 遍历frontmatter内容区域的每一行
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def message_text(msg: dict):
    # 提取消息字典中的内容字符
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    return str(content)


# 接收大模型返回的response里的文本字符串
def llm_text(response):
    return (response.choices[0].message.content or "").strip()
