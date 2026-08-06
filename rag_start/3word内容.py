# 导入python-docx库中的Document类
from docx import Document
from utils.main import printLine
from sentence_transformers import SentenceTransformer
import numpy as np
import re

# 加载预训练的句子嵌入模型
printLine("正在加载句子嵌入模型...")
model = SentenceTransformer("all-MiniLM-L6-v2")
printLine("模型加载完成。")

# 定义函数：从Word文档中提取所有段落文本
def extract_text_from_word(file_path):
    """
    从Word文档中提取所有段落的文本，并以字符串返回。
    :param file_path: Word文档的路径
    :return: 文本内容字符串
    """
    # 加载Word文档
    doc = Document(file_path)
    # 遍历所有段落，将段落文本拼接为一个字符串（以换行符分隔）
    text = "\n".join([para.text for para in doc.paragraphs])
    # 返回拼接后的文本
    return text

# 主程序入口，进行测试调用
if __name__ == "__main__":
    # 指定要读取的Word文件名
    file_path = "前端开发刘春达简历.docx"
    # 调用函数提取Word文本
    result = extract_text_from_word(file_path)
    # 打印提取到的文本内容
    printLine(result)
