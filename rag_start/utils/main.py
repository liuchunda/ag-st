import inspect

# args把未指定名字的收敛成一个元组，kwargs把任意关键字参数收敛成字典
def printLine(*args, **kwargs):
    line = inspect.currentframe().f_back.f_lineno
    sep = "-------------"
    print(f"{sep}{line}")
    print(*args, **kwargs)
    print(f"{sep}{line}")
