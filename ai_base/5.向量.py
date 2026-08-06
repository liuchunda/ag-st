import numpy as np


def euclidean_distance(a, b):
    a = np.array(a)
    b = np.array(b)
    r = a - b # 向量相减 [-3, -3, -3]
    p = r ** 2 # [9, 9, 9]
    sum = np.sum(p) # 27
    sqrt = np.sqrt(sum) # 根号下27=3根号3
    print(sqrt)
    return sqrt


# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

a = [1, 2, 3]
b = [4, 5, 6]
euclidean_distance(a, b)
# print(cosine_similarity(a, b))



