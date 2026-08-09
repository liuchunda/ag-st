print("hello")
from pathlib import Path

# 当前的工作目录
WORKDIR = Path.cwd()
# 设置技能目录为工作目录下面的skills目录
SKILLS_DIR = WORKDIR / "skills"
for dir in sorted(SKILLS_DIR.iterdir()):
    print(dir)
