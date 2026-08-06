from typing import Optional

# 一、Optional（来自 typing，不是 FastAPI 专属）

# 一种类型标注，告诉人和工具：这个值「可以有，也可以没有」。


# 用法（核心就一点）

# def greet(name: Optional[str] = None):


# str | None 是 Python 3.10+ 的写法，现在更常见；Optional[str] 是老写法，意思一样。

