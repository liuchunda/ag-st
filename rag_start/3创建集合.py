from pymilvus import MilvusClient, DataType
from utils.main import printLine

URI = "http://localhost:19530"
DB_NAME = "rensheng"
COLLECTION_NAME = "example"



# 先连默认库，没有 rensheng 就创建
admin = MilvusClient(uri=URI)
printLine(admin.list_databases())
if DB_NAME not in admin.list_databases():
    admin.create_database(DB_NAME)
    print(f"数据库 {DB_NAME} 创建成功")
# else:
#     print(f"数据库 {DB_NAME} 已存在")

# 再连到 rensheng
client = MilvusClient(uri=URI, db_name=DB_NAME)

# 定义 schema：主键 + 128 维向量
schema = client.create_schema(auto_id=True)
schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=128)

if client.has_collection(COLLECTION_NAME):
    print(f"集合 {COLLECTION_NAME} 已存在")
else:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        description="example",
    )
    print(f"集合 {COLLECTION_NAME} 创建成功")

print("当前集合:", client.list_collections())
