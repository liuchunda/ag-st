import numpy as np

# 定义第一个向量
vec1 = np.array([1, 2])
# 定义第二个向量
vec2 = np.array([2, 3])

# 定义计算余弦相似度的函数

#  linear algebra（线性代数）。 linear连贯的、连续的、线性的
# algebra  
#  英  [ˈældʒɪbrə]
def cosine_similarity(a, b):
    # 计算两个向量的点积
    dot_product = np.dot(a, b)#1*2+2*3=2+6=8
    # 计算第一个向量的范数
    norm_a = np.linalg.norm(a)#1平方+2平方=5的平方根=根号5
    # 计算第二个向量的范数
    norm_b = np.linalg.norm(b)#2平方+3平方=4+9=13的平方根=根号13
    # 返回余弦相似度的计算结果
    return dot_product / (norm_a * norm_b)#8 / (根号5 * 根号13) = 8 / (根号65) = 8 / 8.06225774829855 = 0.9923171183340236

# 调用余弦相似度函数计算vec1和vec2的相似度
similarity = cosine_similarity(vec1, vec2)
# 打印余弦相似度结果
print(f"余弦相似度: {similarity}")

# ∥A∥×∥B∥

