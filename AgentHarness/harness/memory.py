from utils import message_text, parse_frontmatter, llm_text
import json
import time
import re
from config import (
    MEMORY_DIR,
    MEMORY_INDEX,
    CONSOLIDATE_THRESHOLD,
    TEXT_ENCODING,
    MODEL_ID,
)
from config import client


def select_relevant_memories(messages, max_items=5):
    # 1.获取所有的记忆文件
    files = list_memory_files()
    if not files:
        return []
    # 初始化保存最近用户消息内容的列表
    recent_texts = []
    # 逆序遍历消息列表，提取最近的三条用户消息
    for msg in reversed(messages):
        if msg.get("role") == "user":
            text = message_text(msg).strip()
            if text:
                recent_texts.append(text)
            if len(recent_texts) >= 3:
                break
    # 将最近三条用户消息再接回正确顺序的字符串
    recent = " ".join(reversed(recent_texts))[:2000]
    if not recent.strip():
        return []
    catelog = "\n".join(
        f"索引：{index} :{file['name']} - {file['description']}"
        for index, file in enumerate(files)
    )

    prompt = (
        "根据近期对话和下方的记忆目录，选出明显相关的记忆索引"
        "仅返回JSON整数数组，例如[0,3]。若无相关则返回[]。\n\n"
        f"近期对话:\n{recent}\n\n记忆目录:\n{catelog}"
    )
    try:
        response = client.chat.completions.create(
            model=MODEL_ID, messages=[{"role": "user", "content": prompt}]
        )
        text = llm_text(response)
        # 用正则匹配结果
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            indices = json.loads(match.group())
            selected = []
            # 遍历记忆文件索引列表
            for idx in indices:
                # 如果是一个整数
                if isinstance(idx, int) and 0 <= idx < len(files):
                    selected.append(files[idx]["filename"])
                    if len(selected) >= max_items:
                        break
            return selected
    except Exception:
        return []

    # 兜底的方案，近的消息中长度大于3的单词降级检索
    keywords = [word.lower() for word in recent.split() if len(word) > 3]
    selected = []
    for f in files:
        text = (f["name"] + " " + f["description"]).lower()
        if any(kw in text for kw in keywords):
            selected.append(f["filename"])
            if len(selected) > max_items:
                break
    return selected


def read_memory_file(filename):
    path = MEMORY_DIR / filename
    if not path.exists():
        return None
    return path.read_text(encoding=TEXT_ENCODING, errors="replace")


# 加载与对话相关的记忆内容，拼成字符串返回
def load_memories(messages: list):
    # 先出对话相关的记忆文件名
    selected_files = select_relevant_memories(messages)
    if not selected_files:
        return ""
    parts = ["<relevant_memories>"]
    for filename in selected_files:
        content = read_memory_file(filename)
        if content:
            parts.append(content)
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)


# 列出的记忆文件，并返回一个包含所有的记忆文件的元数据的字典列表
def list_memory_files():
    result = []
    # 遍历记忆目录下所有的markdown文件，并按名称排序  排序是为了保证结果稳定
    for file in sorted(MEMORY_DIR.glob("*.md")):
        if file.name == "MEMORY.md":
            continue
        raw = file.read_text(encoding=TEXT_ENCODING, errors="replace")
        meta, body = parse_frontmatter(raw)
        result.append(
            {
                "filename": file.name,  # 文件名
                "name": meta.get(
                    "name", file.stem
                ),  # 记忆的名称 file.stem指的是文件对象属性指的是不包含扩展名的文件名
                "description": meta.get("description", ""),  # 描述
                "type": meta.get(
                    "type", "user"
                ),  # 类型 user project feedback reference
                "body": body,
            }
        )
    return result


# 那file.name和file.stem是一样的？name = 红楼梦.md   stem = 红楼梦


# 重建记忆文件的索引文件
def _rebuild_index():
    lines = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        raw = f.read_text(encoding=TEXT_ENCODING, errors="replace")
        meta, body = parse_frontmatter(raw)
        name = meta.get("name", f.stem)
        desc = meta.get("description", body.split("\n")[0][:80])
        lines.append(f"- [{name}]({f.name}) - {desc}")
    MEMORY_INDEX.write_text(
        "\n".join(lines) + "\n" if lines else "", encoding=TEXT_ENCODING
    )


def write_memory_file(name, mem_type, description, body):
    # 生成文件名 slug (小写 空格 和斜杠都替换成连字符)
    slug = name.lower().replace(" ", "-").replace("/", "-")
    # 构建完整的文件路径
    filepath = MEMORY_DIR / f"{slug}.md"
    # 按frontmatter的格式写入到文件中去
    filepath.write_text(
        f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}\n---\n\n{body}\n",
        encoding=TEXT_ENCODING,
    )
    _rebuild_index()
    return filepath


# 从最近的对话中提取新的记忆
def extract_memories(messages: list):
    # 初始化保存对话片段的列表
    dialogue_parts = []
    # 只处理最近的10条消息
    for msg in messages[-10:]:
        role = msg.get("role", "?")
        text = message_text(msg).strip()
        # 如果有文本内容，则格式化后添加到对话片段列表中
        if text:
            dialogue_parts.append(f"{role}:{text}")
    # 合并所有的对话片段为多行字符串
    dialogue = "\n".join(dialogue_parts)
    if not dialogue.strip():
        return
    # 获取已经存在的记忆文件列表
    existing = list_memory_files()
    # 构建已经存在的记忆描述文件
    existing_desc = (
        "\n".join(f"- {m['name']}: {m['description']}" for m in existing)
        if existing
        else "(无)"
    )
    prompt = (
        "从对话中提取用户的偏好，约束或项目事实"
        "返回JSON数组，每项：{name,type,description,body}。\n"
        "- name: 短kebab-case标识符\n"
        "- type: user|feedback|project|reference\n"
        "- description: 行摘要供索引检索\n"
        "- body: markdown详情\n"
        "若无新内容或已被现有的记忆覆盖，返回 []。\n\n"
        f"现有记忆:\n{existing_desc}\n\n对话:\n{dialogue}"
    )
    try:
        response = client.chat.completions.create(
            model=MODEL_ID, messages=[{"role": "user", "content": prompt}]
        )
        text = llm_text(response)
        # 用正则匹配结果
        match = re.search(r"\[.*\]", text, re.DOTALL)
        # 如果没找到
        if not match:
            return
        items = json.loads(match.group())
        if not items:
            return
        count = 0
        names = []
        for mem in items:
            name = mem.get("name", f"memory_{int(time.time())}")
            names.append(name)
            mem_type = mem.get("type", "user")
            desc = mem.get("description", "")
            body = mem.get("body", "")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)
                count += 1
        if count:
            print(f"\n\x1b[33m[记忆：提取了{count}条新的记忆] {','.join(names)}\x1b[0m")

    except Exception:
        pass


# 合并记忆库，将冗余的和冲突的信息归并，并限制数量
def consolidate_memories():
    files = list_memory_files()
    # 如果文件数量小于阈值的话
    if len(files) < CONSOLIDATE_THRESHOLD:
        return
    # 构建所有的记忆内容的目录文本，用于合并提示
    catelog = "\n\n".join(
        f"## {f['filename']}\nname:{f['name']}\ndescription:{f['description']}\n{f['body']}"
        for f in files
    )
    prompt = (
        "合并以下记忆文件，规则：\n"
        "1.重复项合并为1条\n"
        "2.删除过时的/矛盾的记忆\n"
        "3.总数控制在30条以内\n"
        "4.优先保留重要的用户偏好"
        "返回JSON数组,每项：{name,type,description,body}\n\n"
        f"{catelog}"
    )
    try:
        response = client.chat.completions.create(
            model=MODEL_ID, messages=[{"role": "user", "content": prompt}]
        )
        text = llm_text(response)
        # 用正则匹配结果
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        # 清空除MEMORY.md之外的所有的记忆文件 f.unlink指的是删除这个文件
        for f in MEMORY_DIR.glob("*.md"):
            if f.name != "MEMORY.md":
                f.unlink()
        # 遍历合并后的记忆文件并写入硬盘
        for mem in items:
            name = mem.get("name", f"memory_{int(time.time())}")
            mem_type = mem.get("type", "user")
            desc = mem.get("description", "")
            body = mem.get("body", "")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)
        print(f"\n\x1b[33m[记忆：已经整理{len(files)}->{len(items)}条记忆] \x1b[0m")
    except Exception:
        pass
