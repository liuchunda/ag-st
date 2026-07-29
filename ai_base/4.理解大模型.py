# 定义语料，每个句子中的词和标点由空格分隔
from collections import defaultdict

corpus = [
    "天气 预报 说 长沙 明天 有 暴雨 。",
    "出门 请 携带 雨具 。",
    "这里 是 一座 历史悠久 的 美丽 城市 。",
    "大雨 在 下午 停了 ， 太阳 出来 了 。",
    "后天 大部分 地区 晴朗 温暖 。",
    "强降雨 可能 造成 低洼 地区 洪涝 。",
    "国王 的 女儿 善良 勇敢 。",
    "公主 住 在 森林 附近 的 城堡 里 。",
    "很久 以前 一位 国王 住 在 遥远 的 国度 。",
    "她 每天 喜欢 读书 和 学习 新 知识 。",
    "根据 接口 信息 定 位 错误 原因 。",
    "多 匹配 组件 定位， 去重 优化",
    "明天 是个 好日子",
    "明天 是个 不好 的 日子",
    "天气 晴朗， 气温 适宜， 适合 外出 。",
]

def split_sentence(sentence):
    return sentence.split(" ")

words_per_sentence = [split_sentence(s) for s in corpus]
# print(words_per_sentence,19)
# words_per_sentence =[
# ['天气', '预报', '说', '长沙', '明天', '有', '暴雨', '。'],
# ['出门', '请', '携带', '雨具', '。'],
# ['这里', '是', '一座', '历史悠久', '的', '美丽', '城市', '。'],
# ['大雨', '在', '下午', '停了', '，', '太阳', '出来', '了', '。'],
# ['后天', '大部分', '地区', '晴朗', '温暖', '。'],
# ['强降雨', '可能', '造成', '低洼', '地区', '洪涝', '。'],
# ['国王', '的', '女儿', '善良', '勇敢', '。'],
# ['公主', '住', '在', '森林', '附近', '的', '城堡', '里', '。'],
# ['很久', '以前', '一位', '国王', '住', '在', '遥远', '的', '国度', '。'],
# ['她', '每天', '喜欢', '读书', '和', '学习', '新', '知识', '。']
# ]

all_words = set()
# all_words = {'天气', '预报', '说', '长沙', '明天', '有', '暴雨', '。', '出门', '请', '携带', '雨具', '。', '这里', '是', '一座', '历史悠久', '的', '美丽', '城市', '。', '大雨', '在', '下午', '停了', '，', '太阳', '出来', '了', '。', '后天', '大部分', '地区', '晴朗', '温暖', '。', '强降雨', '可能', '造成', '低洼', '地区', '洪涝', '。', '国王', '的', '女儿', '善良', '勇敢', '。', '公主', '住', '在', '森林', '附近', '的', '城堡', '里', '。', '很久', '以前', '一位', '国王', '住', '在', '遥远', '的', '国度', '。', '她', '每天', '喜欢', '读书', '和', '学习', '新', '知识', '。'}
for words in words_per_sentence:
        for word in words:
            all_words.add(word)



# words_per_sentence =[
# ['天气', '预报', '说', '长沙', '明天', '有', '暴雨', '。'],
# ['出门', '请', '携带', '雨具', '。'],
# ['这里', '是', '一座', '历史悠久', '的', '美丽', '城市', '。'],
# ['大雨', '在', '下午', '停了', '，', '太阳', '出来', '了', '。'],
# ['后天', '大部分', '地区', '晴朗', '温暖', '。'],
# ['强降雨', '可能', '造成', '低洼', '地区', '洪涝', '。'],
# ['国王', '的', '女儿', '善良', '勇敢', '。'],
# ['公主', '住', '在', '森林', '附近', '的', '城堡', '里', '。'],
# ['很久', '以前', '一位', '国王', '住', '在', '遥远', '的', '国度', '。'],
# ['她', '每天', '喜欢', '读书', '和', '学习', '新', '知识', '。']
# ]
pair_count = defaultdict(lambda: defaultdict(int))
for words in words_per_sentence:
    for i in range(len(words) - 1):
        pair_count[words[i]][words[i + 1]] += 1

# pair_count
# {
#     '天气': {'预报': 1},
#     '预报': {'说': 1},
#     '说': {'长沙': 1},
#     '长沙': {'明天': 1},
#     '明天': {'有': 1},
#     '有': {'暴雨': 1},
#     '暴雨': {'。': 1},
#     '地区': {'洪涝': 1,'晴朗': 1},
# }
# print(pair_count,20)
next_word_prob = {}
for current_word, count_map in pair_count.items():
    # current_word 
    # '天气'
    # count_map
    # {'预报': 1,'晴朗': 1}
    total = sum(count_map.values())
    next_word_prob[current_word] = {
       word: count / total for word, count in count_map.items()
   }

# next_word_prob = {
#     '天气': {'预报': 1/2,'晴朗': 1/2},
#     '预报': {'说': 1},
#     '说': {'长沙': 1},
#     '长沙': {'明天': 1},
#     '明天': {'有': 1},
#     '有': {'暴雨': 1},
#     '暴雨': {'。': 1},
# }

def complete_sentence(current_word):
    result = []
    if not current_word:
        return None
    if current_word not in all_words:
        return None
    result.append(current_word)
    next_word = get_next_word(current_word)
    while next_word:
        result.append(next_word)
        next_word = get_next_word(next_word)
    return "".join(result)

def get_next_word(word):
    if word not in next_word_prob:
        return None
    candidates = next_word_prob[word]
    max_prob_word = max(candidates.items(), key=lambda x: x[1])
    # max_prob_word = ('预报', 1/2)
    return max_prob_word[0]

print(complete_sentence("明天"),21)