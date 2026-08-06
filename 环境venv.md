venv是python自带的包

python -m venv .venv          # 创建虚拟环境
source .venv/bin/activate     # 激活（终端提示符前常出现 (.venv)）
pip install fastapi           # 包只装进这个环境
deactivate                    # 退出虚拟环境
