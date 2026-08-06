# asyncio = 调度器

# 在一个线程里决定：现在跑哪个协程、谁在 await 就让出
# 职责：管理异步任务怎么切换
# GIL = 互斥锁（约束）

# 规定：同一时刻通常只有一个线程能执行 Python 字节码
# 职责：不是分配任务，而是 防止多线程同时解释执行 Python 码
# 多线程谁跑、何时切换，主要还是 OS / 解释器线程调度；GIL 只是它们必须抢的那把锁


# GIL（Global Interpreter Lock，全局解释器锁） 是 CPython 里的一把 进程级互斥锁：
# 同一个进程中，同一时刻通常只有一个线程在执行 Python 字节码。
# 对象有引用计数；多线程同时改引用计数很容易出竞态，加一把大锁最省事。
# 扩展作者默认可以假设「不会有两个 Python 线程同时在解释器里瞎改对象」。

# 去掉 GIL 成本极高（要改对象模型、GC、大量库）。所以 CPython 一直保留；其他实现（如 Jython、IronPython）可以没有 GIL，但主流还是 CPython。

# 作用
# 保护解释器内部状态
# 简化线程安全（解释器层面）
# 副作用：限制多线程并行

# 1. 线程 A 想执行 Python 字节码 → 先获取 GIL
# 2. A 持有 GIL，执行一段时间字节码（或若干条指令）
# 3. A 到达切换点 / 主动释放（常见：I/O、sleep、或解释器定期检查）
# 4. 释放 GIL → 线程 B 可能抢到 → B 开始执行字节码
# 5. 

# 同一时刻：大致只有一个线程在跑 Python 字节码
# 不是永远不切换：会在 I/O、等待、或一定条件后释放，让别的线程跑
# I/O 密集：线程在等网络/磁盘时通常会放掉 GIL，其他线程能继续 → 多线程仍有用
# CPU 密集纯 Python：多线程往往 抢同一把 GIL，甚至更慢（切换开销）
# 很多 C 扩展（numpy 算矩阵、部分加密/压缩）在算重活时会 主动释放 GIL → 这时可真并行

# 会让出锁
# 1. 网络 I/O
# urllib.request.urlopen("https://example.com").read()

# 2. 文件 I/O
# # 读大文件等待磁盘时，一般会释放 GIL
# with open("big.bin", "rb") as f:
#     data = f.read()

# 3. time.sleep
# import time
# time.sleep(1)  # 睡眠期间释放 GIL

# 4. 等线程结束 / 线程间等待
# mport threading
# t = threading.Thread(target=lambda: time.sleep(2))
# t.start()
# t.join()  # 等待期间当前线程不占着算 Python 字节码


# 5. 很多原生库的重计算（释放 GIL）
# import numpy as np
# a = np.random.rand(2000, 2000)
# b = np.random.rand(2000, 2000)
# # 矩阵乘法多在 C/Fortran 里算，期间常释放 GIL
# c = a @ b


# 6. 定时切换（纯计算也会被打断，但不是“去做 I/O”）
# import sys
# sys.setswitchinterval(0.005)  # 切换检查间隔（默认约 5ms）
# # 纯 Python 死循环也会周期性检查并可能让出 GIL
# while True:
#     x = 1 + 1