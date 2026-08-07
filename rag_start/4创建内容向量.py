# 导入句子嵌入模型
from sentence_transformers import SentenceTransformer

# 导入numpy用于数值计算
import numpy as np

# 导入正则表达式模块
import re

from utils.main import printLine

# 加载预训练的句子嵌入模型
print("正在加载句子嵌入模型...")
model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
print("模型加载完成。")


# 定义基于语义的分块器类
class SemanticChunker:
    # 初始化方法，设置窗口大小和相似度阈值
    def __init__(self, window_size=2, threshold=0.85):
        # 设置每个窗口包含的句子数
        self.window_size = window_size
        # 设置相邻窗口的相似度阈值
        self.threshold = threshold
        # 日志：输出初始化参数
        print(
            f"SemanticChunker初始化，窗口大小: {window_size}，相似度阈值: {threshold}"
        )

    # 创建分块文档的方法
    def create_documents(self, text):
        # 使用正则表达式按中英文标点和换行分割句子
        # 当正则表达式中使用捕获分组时，分隔符会包含在结果中
        print("正在分割原始文本为句子...")
        sentences = re.split(r"(。|！|？|\!|\?|\.|\n)", text)
        # 初始化句子列表
        printLine(text)
        printLine(sentences)
        sents = []
        # 遍历分割后的句子和标点，合并为完整句子
        for i in range(0, len(sentences) - 1, 2):
            # 拼接句子内容和分隔符
            s = sentences[i].strip() + sentences[i + 1].strip()
            # 如果拼接后不为空，则加入句子列表
            if s.strip():
                sents.append(s)
        # 日志：输出分割后的句子数量
        print(f"分割得到 {len(sents)} 个句子。")
        printLine(sents)
        # 初始化分块列表
        docs = []
        # 设置起始索引
        start = 0
        # 使用滑动窗口将句子分组
        # 窗口用于聚合上下文，窗口合并多个句子，嵌入能表达更完整的语义，让语义比较更稳定、更可靠
        print("正在使用滑动窗口进行初步分块...")
        while start < len(sents):
            # 计算窗口结束位置
            end = min(start + self.window_size, len(sents))
            # 获取当前窗口的句子
            window = sents[start:end]
            # 合并窗口内句子为一个块
            docs.append("".join(window))
            # 移动到下一个窗口
            start = end
        # 日志：输出初步分块数量
        print(f"初步分块完成，共 {len(docs)} 个块。")
        # 计算每个窗口的嵌入向量
        print("正在计算每个块的嵌入向量...")
        printLine(docs)
        embeddings = model.encode(docs)
        printLine(embeddings)
        # 初始化分割点列表，起始点为0
        split_points = [0]
        # 遍历相邻窗口，计算相似度
        print("正在计算相邻块之间的相似度...")
        for i in range(1, len(docs)):
            # 计算余弦相似度
            sim = np.dot(embeddings[i - 1], embeddings[i]) / (
                np.linalg.norm(embeddings[i - 1]) * np.linalg.norm(embeddings[i])
            )
            # 日志：输出每对块的相似度
            print(f"块 {i} 与块 {i-1} 的相似度为: {sim:.4f}")
            # 如果相似度低于阈值，则作为新的分割点
            if sim < self.threshold:
                print(f"相似度低于阈值({self.threshold})，在位置 {i} 添加分割点。")
                split_points.append(i)
        # 初始化最终分块结果列表
        result = []
        # 遍历所有分割点，生成最终文本块
        print("正在根据分割点生成最终分块结果...")
        for i in range(len(split_points)):
            # 当前块的起始索引
            start = split_points[i]
            # 当前块的结束索引
            end = split_points[i + 1] if i + 1 < len(split_points) else len(docs)
            # 合并该范围内的窗口为一个块
            chunk = "".join(docs[start:end])
            # 如果块内容不为空，则加入结果列表
            if chunk.strip():
                print(f"生成第 {len(result)+1} 个块，内容长度: {len(chunk)}")
                result.append(chunk)
        # 返回所有分块
        print(f"最终分块完成，共 {len(result)} 个块。")
        return result


# 创建语义分块器对象，设置窗口大小和相似度阈值
print("正在创建语义分块器对象...")
semantic_splitter = SemanticChunker(window_size=2, threshold=0.85)

# 准备需要分割的长文本
print("准备待分割的长文本...")
long_text = """今天天气晴朗，适合去公园散步。

量子力学中的叠加态是描述粒子同时处于多个状态的数学工具。

Windows命令行中复制文件可以使用copy命令。

大熊猫主要以竹子为食，是中国的国宝。

欧拉公式被誉为“最美的数学公式”。"""

# 执行文本分割，得到分块结果
print("开始执行文本分割...")
documents = semantic_splitter.create_documents(long_text)
# documents=[
# '今天天气晴朗，适合去公园散步。',
# '量子力学中的叠加态是描述粒子同时处于多个状态的数学工具。',
# 'Windows命令行中复制文件可以使用copy命令。',
# '大熊猫主要以竹子为食，是中国的国宝。',
# '欧拉公式被誉为“最美的数学公式”。'
# ]
# 打印分割结果，显示每个块的内容
print(f"总共分割为 {len(documents)} 个块:\n")
for i, doc in enumerate(documents, 1):
    # 打印当前块的编号
    print(f"=== 第 {i} 个块 ===")
    # 打印当前块的内容
    print(doc)