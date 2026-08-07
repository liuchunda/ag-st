# 导入默认字典，用于分区聚合
from collections import defaultdict

# 导入结巴分词工具
import jieba

# 定义示例文档数据，每个文档包含“id”、“分区键”、“内容”
documents = [
    {"id": 1, "partition_key": "张", "content": "张三喜欢编程和电脑游戏"},
    {"id": 2, "partition_key": "李", "content": "李四热爱计算机科学"},
    {"id": 3, "partition_key": "王", "content": "王五喜欢阅读技术书籍"},
    {"id": 4, "partition_key": "张", "content": "张杰钟爱笔记本电脑"},
]

# 定义同义词映射，“键”为代表词，“值”为同义词集合（用于扩展匹配）
synonym_map = {
    "电脑": {"电脑", "计算机", "PC"},
    "编程": {"编程", "程序设计"},
}

# 对输入文本进行分词（搜索模式），返回词元列表
def simple_tokenize(text: str):
    """说明：使用 jieba 搜索模式，得到更细粒度的词元"""
    result=[token for token in jieba.lcut_for_search(text) if token.strip()]
    print(25,result,25)
    return result

# 根据“分区键”对文档进行聚合，返回分区字典
def build_partitions(docs):
    """说明：按照分区键将文档聚合"""
    partitions = defaultdict(list)
    for doc in docs:
        partitions[doc["partition_key"]].append(doc)
    return partitions

# 在所有分区内查找包含指定关键词（或同义词）的文档
def match_query(partitions, keyword: str, use_synonym=True):
    """说明：在指定分区内执行匹配，支持同义词扩展"""
    # 构建本次要匹配的词集合，默认为仅包含keyword
    tokens_to_match = {keyword}
    # 如果启用同义词且keyword在同义词表中，则扩展为所有同义词
    if use_synonym and keyword in synonym_map:
        tokens_to_match = synonym_map[keyword]

    # 结果列表，用于收集匹配文档
    results = []
    # 遍历每个分区和分区下的文档
    for partition_key, docs in partitions.items():
        for doc in docs:
            # 对文档内容进行分词
            tokens = simple_tokenize(doc["content"])
            # tokens=
            # ['张', '三', '喜欢', '编程', '和', '电脑', '游戏']
            # 判断有无交集（有则说明匹配）
            if tokens_to_match.intersection(tokens):
                results.append((partition_key, doc["id"], doc["content"]))
    # 返回所有匹配结果
    # results=
    # [('张', 1, '张三喜欢编程和电脑游戏'), ('张', 4, '张杰钟爱笔记本电脑')]
    return results

# 程序主入口
if __name__ == "__main__":
    # 按分区键聚合文档
    partitions = build_partitions(documents)
    # partitions=
    # {
    #     "张": [{"id": 1, "partition_key": "张", "content": "张三喜欢编程和电脑游戏"}, {"id": 4, "partition_key": "张", "content": "张杰钟爱笔记本电脑"}],
    #     "李": [{"id": 2, "partition_key": "李", "content": "李四热爱计算机科学"}],
    #     "王": [{"id": 3, "partition_key": "王", "content": "王五喜欢阅读技术书籍"}]
    # }
    # 示例1：只匹配“电脑”本词
    hits = match_query(partitions, keyword="电脑", use_synonym=False)
    # hits=
    # [('张', 1, '张三喜欢编程和电脑游戏'), ('张', 4, '张杰钟爱笔记本电脑')]
    print("仅匹配“电脑”的结果：")
    for row in hits:
        print(row)

    # 示例2：启用同义词匹配（“电脑”≈“计算机”）
    hits_with_synonym = match_query(partitions, keyword="电脑", use_synonym=True)
    print("\n启用同义词匹配后的结果：")
    for row in hits_with_synonym:
        print(row)