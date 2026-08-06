# 传统方式
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# uv 方式
uv sync
uv run python test.py

# 项目管理
uv init my-project          # 创建新项目
uv init .                     # 在当前目录初始化
uv init --python 3.10 my-project  # 指定 Python 版本

uv sync                       # 同步依赖（读 pyproject.toml + uv.lock）
uv sync --upgrade               # 升级所有依赖
uv lock                         # 只更新锁文件，不安装