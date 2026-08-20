# 导入 pymilvus 模块中的 Collection 类和 connections 连接模块
from pymilvus import Collection, connections
# 导入随机数生成模块，用于生成向量数据
import random

# 连接到 Milvus 数据库，指定别名、主机地址、端口号和数据库名称
connections.connect("default", host="localhost", port="19530", db_name="rensheng")
# 获取名为 "example" 的集合对象，后续操作都基于此集合
collection = Collection("example")

# 定义要创建的分区名称
partition_name = "partition_2"
# 判断集合中是否已经存在该分区，如果不存在则创建，否则提示已存在
if partition_name not in [p.name for p in collection.partitions]:
    collection.create_partition(partition_name)
    print(f"分区 '{partition_name}' 创建成功")
else:
    print(f"分区 '{partition_name}' 已存在")

# 生成 10 个随机的 128 维向量，假设集合的 schema 中 embedding 字段为 128 维
vectors = [[random.random() for _ in range(128)] for _ in range(10)]
# 组织插入数据的格式，按 schema 字段顺序构造 data 列表
data = [vectors]

# 向指定分区插入数据，返回插入结果
insert_result = collection.insert(data, partition_name=partition_name)
# 打印插入数据的条数
print(f"已向分区 '{partition_name}' 插入 {insert_result.insert_count} 条数据")
# 将内存中的数据写入磁盘，保证持久化
collection.flush()
# 加载指定分区的数据到内存，提升后续搜索效率
collection.load(partition_names=[partition_name])
# 打印分区已加载到内存的提示
print(f"分区 '{partition_name}' 已加载到内存")
# 设置搜索参数：距离类型为 L2（欧式距离），nprobe 用于控制扫描的范围
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

# 生成一个随机的 128 维查询向量
query_vector = [random.random() for _ in range(128)]

# 在指定的分区中执行向量搜索，搜寻最相近的前5个向量
results = collection.search(
    data=[query_vector],
    anns_field="embedding",
    param=search_params,
    limit=5,
    partition_names=[partition_name],  # 指定搜索的范围仅限该分区
)
# 打印原始的搜索结果
print(results)
# 遍历每条搜索结果，逐条打印其 id 和 距离
for hits in results:
    for hit in hits:
        print(f"id: {hit.id}, distance: {hit.distance}")

# 打印当前集合中所有分区的名称
print("当前集合所有分区：", [p.name for p in collection.partitions])
# 先从内存释放
collection.release(partition_names=[partition_name])  
# 如果需要删除分区（危险操作，一般不用），可以取消下面的注释执行删除
collection.drop_partition(partition_name)
print(f"分区 '{partition_name}' 已删除")
print("当前集合所有分区：", [p.name for p in collection.partitions])
