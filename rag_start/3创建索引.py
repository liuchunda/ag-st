# 导入 pymilvus 集合和连接模块
from pymilvus import Collection, connections
from utils.main import printLine
# 连接到 Milvus 数据库，指定主机、端口和数据库名称
connections.connect("default", host="localhost", port="19530", db_name="rensheng")
# 获取名为 "example" 的集合对象
collection = Collection("example")

# 定义索引参数配置
index_params = {
    "metric_type": "L2",  # 距离度量方式：L2、IP、COSINE
    "index_type": "IVF_FLAT",  # 索引类型 Inverted File with Flat（倒排文件+暴力遍历）
    "params": {"nlist": 128},  # nlist 越大召回率越高，速度越慢
}

# 为向量字段创建索引
collection.create_index("embedding", index_params)
# 打印索引创建成功信息
printLine("索引创建成功")
