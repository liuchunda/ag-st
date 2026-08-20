# 导入 pymilvus 连接模块
from pymilvus import connections

# 连接到 Milvus 服务器（本地或远程）
# 使用默认连接别名，连接到本地主机的19530端口，数据库名为rensheng
connections.connect("default", host="localhost", port="19530", db_name="rensheng")

# 检查连接状态
# 验证名为"default"的连接是否存在，返回True表示连接成功
print(connections.has_connection("default"))  # True 表示连接成功
