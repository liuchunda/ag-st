from config import SKILLS_DIR, TEXT_ENCODING
from utils import parse_frontmatter

# 定义一个全局字典，用于存放技能信息，键为字符串，值为字典
SKILL_REGISTRY = {}


# 扫描技能目录下面所有的技能
def _scan_skills():
    # 如果技能目录不存在，则直接返回
    if not SKILLS_DIR.exists():
        return
    # 遍历技能目录下面所有的子目录，按目录名称排序
    for dir in sorted(SKILLS_DIR.iterdir()):
        # 如果不是目录，则跳过
        if not dir.is_dir():
            continue
        # 构建描述文件的路径
        manifest = dir / "SKILL.md"
        # 如果描述文档不 存在则跳过
        if not manifest.exists():
            continue
        # 读取文件内容
        raw = manifest.read_text(encoding=TEXT_ENCODING, errors="replace")
        # 即系meta数据，获取 元信息和正文内容
        meta, _body = parse_frontmatter(raw)
        name = meta.get("name", dir.name)
        description = meta.get(
            "description", raw.split("\n")[0].lstrip("#").strip()
        ) + meta.get("when_to_use", "")
        when_to_use = meta.get("when_to_use", "")
        # 将技能信息存入全局注册表里
        SKILL_REGISTRY[name] = {
            "name": name,  # 技能名称
            "description": description,  # 技能描述
            "content": raw,  # 技能正文
        }


_scan_skills()


def run_load_skill(name: str):
    skill = SKILL_REGISTRY.get(name)
    if not skill:
        return f"未找到技能{name}"
    print(f"\x1b[90m [技能] {name} 已经加载 \x1b[0m")
    return skill["content"]
