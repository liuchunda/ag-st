# 包目录 + __init__.py = 一个包；import 包名 得到的是这个包的模块对象。
# 模块对象里有什么，看 __init__.py 里定义或 from .xxx import Yyy 导出了什么。
# 包名 这个变量不是写在 __init__.py 里的，是 import 包名 时由 Python 创建并绑定的。
# from 包名 import Yyy 只取出模块里的某个名字；import 包名 拿整个模块，用 包名.Yyy 访问。
# __main__.py 只服务 python -m 包名，和「能 import 什么」无关。