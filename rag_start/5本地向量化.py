# 从sentence_transformers库中导入SentenceTransformer类
from sentence_transformers import SentenceTransformer

# 加载预训练的句子嵌入模型"all-MiniLM-L6-v2"
model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)

# 定义一个函数，用于获取输入文档内容的向量表示
def get_sentence_embedding(doc_content):
    # 使用模型对文档内容进行编码，得到嵌入向量
    embedding = model.encode(doc_content)
    # 返回嵌入向量
    return embedding


# 定义一个示例文档内容
doc_content = "这是一个示例文档"
# 获取示例文档的嵌入向量
embedding = get_sentence_embedding(doc_content)
# 打印嵌入向量
print(embedding)
