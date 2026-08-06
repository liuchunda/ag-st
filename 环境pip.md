pip install requests   # 自动从 PyPI 下载并处理依赖
pip list               # 查看已安装的包
pip freeze > requirements.txt   # 导出依赖文件
pip install -r requirements.txt   # 从依赖文件安装


# 安装
pip install requests                  # 最新版
pip install django==4.2.0             # 指定版本
pip install numpy>=1.21               # 最低版本
pip install requests pandas numpy     # 多个包
pip install -r requirements.txt       # 从文件安装

# 卸载
pip uninstall requests

# 升级
pip install --upgrade requests        # 简写：pip install -U requests

# 查看
pip list
pip show requests