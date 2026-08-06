from pymilvus import MilvusClient
# from pymilvus import connections
client = MilvusClient(uri="http://localhost:19530",port=19530, db_name="default")

print(client.get_server_version())
print(client.list_databases())
print(client.list_collections())
