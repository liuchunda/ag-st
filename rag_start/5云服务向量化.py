# 导入os模块，用于读取环境变量
import os

# 导入requests库，用于发送HTTP请求
import requests

# 设置文本向量API的URL
VOLC_EMBEDDINGS_API_URL = "https://ark.cn-beijing.volces.com/api/v3/embeddings"
# 设置API密钥
VOLC_API_KEY = "d52e49a1-36ea-44bb-bc6e-65ce789a72f6"

# 定义获取文档向量的函数，参数为文档内容
def get_doubao_embedding(doc_content):
    # 构造请求头，包含内容类型和认证信息
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VOLC_API_KEY}",
    }
    # 构造请求体，指定模型和输入内容
    payload = {"model": "doubao-embedding-text-240715", "input": doc_content}
    # 发送POST请求到向量API，获取响应
    response = requests.post(VOLC_EMBEDDINGS_API_URL, json=payload, headers=headers)
    # 判断响应状态码是否为200，表示请求成功
    if response.status_code == 200:
        # 解析响应的JSON数据
        data = response.json()
        # 提取嵌入向量
        embedding = data["data"][0]["embedding"]
        # 返回嵌入向量
        return embedding
    else:
        # 如果请求失败，抛出异常并输出错误信息
        raise Exception(f"Embedding API error: {response.text}")

# 定义待处理的文档内容
doc_content = "这是一个示例文档"
# 调用函数获取嵌入向量
embedding = get_doubao_embedding(doc_content)
# 打印嵌入向量
print(embedding)