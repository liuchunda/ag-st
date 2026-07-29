
# NumPy = 用 ndarray 高效做向量/矩阵加减乘和统计；AI 里的 Embedding，本质上就是一串 NumPy 数字。

# Numerical Python
# Numerical英  [ˈnjuːmərɪkl]  adj. 数字的；n. 数字；

# ndarray类型 n-dimensional array
# dimensional英  [daɪˈmenʃən(ə)l]  adj. 维度的

import os
# 从 sentence_transformers 导入 SentenceTransformer
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
import numpy as np
print(model)
def consine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# print(consine_similarity([1, 2, 3], [4, 5, 6]))

# 定义第一个要比较的文本
text_a = "我喜欢吃苹果"
# 定义第二个要比较的文本
text_b = "梨是很好吃的水果"
# 定义第三个要比较的文本
text_c = "篮球打起来很过瘾"

embedding_a = model.encode(text_a)
embedding_b = model.encode(text_b)
embedding_c = model.encode(text_c)

print(consine_similarity(embedding_a, embedding_b))
print(consine_similarity(embedding_a, embedding_c))
print(consine_similarity(embedding_b, embedding_c))
print(type(embedding_c),28)