# 导入os模块，用于路径和文件操作
import os
# 导入Optional类型用于类型注解（本文件其实未用到）
from typing import Optional

# 从 6db 模块导入保存文本到数据库的函数
# 文件名以数字开头，不能用 from 6db import，需用 importlib
from importlib import import_module

save_text_to_db = import_module("6db").save_text_to_db
# 导入extract模块，用于处理各种格式的文本提取
import extract
# 导入递归字符分割器，用于文本分块
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 导入logging模块，用于日志记录
import logging

# 配置日志的输出格式和日志级别
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
# 获取当前模块的logger对象
logger = logging.getLogger(__name__)

# 默认分块大小
DEFAULT_CHUNK_SIZE = 200
# 默认分块重叠长度
DEFAULT_CHUNK_OVERLAP = 30
# 默认集合名称
DEFAULT_COLLECTION_NAME = "rag"

# 定义自动根据文件类型提取文本内容的函数
def extract_text_auto(file_path: str) -> str:
    """
    根据文件类型自动提取文本内容

    参数:
        file_path (str): 文件路径

    返回:
        str: 提取的文本内容

    异常:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件类型
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        # 文件不存在时记录错误日志
        logger.error(f"文件不存在: {file_path}")
        # 抛出文件不存在异常
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 获取文件扩展名，并转换为小写
    ext = os.path.splitext(file_path)[-1].lower()
    
    try:
        # 如果是pdf文件
        if ext == ".pdf":
            logger.info(f"检测到PDF文件，开始提取文本: {file_path}")
            return extract.extract_pdf_text(file_path)
        # 如果是Word文档
        elif ext in [".docx", ".doc"]:
            logger.info(f"检测到Word文件，开始提取文本: {file_path}")
            return extract.extract_text_from_word(file_path)
        # 如果是Excel文件
        elif ext in [".xlsx", ".xls"]:
            logger.info(f"检测到Excel文件，开始提取文本: {file_path}")
            return extract.extract_text_from_excel(file_path)
        # 如果是PPT文件
        elif ext in [".pptx", ".ppt"]:
            logger.info(f"检测到PPT文件，开始提取文本: {file_path}")
            return extract.extract_ppt_text(file_path)
        # 如果是HTML文件
        elif ext in [".html", ".htm"]:
            logger.info(f"检测到HTML文件，开始提取文本: {file_path}")
            return extract.extract_text_from_html(file_path)
        # 如果是XML文件
        elif ext == ".xml":
            logger.info(f"检测到XML文件，开始提取文本: {file_path}")
            return extract.extract_xml_text(file_path)
        # 如果是CSV文件
        elif ext == ".csv":
            logger.info(f"检测到CSV文件，开始提取文本: {file_path}")
            return extract.read_csv_to_text(file_path)
        # 如果是JSON文件
        elif ext == ".json":
            logger.info(f"检测到JSON文件，开始提取文本: {file_path}")
            return extract.extract_text_from_json(file_path)
        # 如果是纯文本、Markdown、JSONL文件
        elif ext in [".md", ".txt", ".jsonl"]:
            logger.info(f"检测到文本/Markdown/JSONL文件，开始读取: {file_path}")
            return extract.read_text_file(file_path)
        # 其余不支持的文件类型
        else:
            logger.error(f"不支持的文件类型: {ext}")
            raise ValueError(f"不支持的文件类型: {ext}")
    # 捕获全部异常，记录日志并抛出
    except Exception as e:
        logger.error(f"提取文件内容失败: {file_path}, 错误: {str(e)}")
        raise

# 定义文档入库的主流程函数
def doc_to_vectorstore(
    file_path: str,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """
    将文档提取、分块并保存到向量数据库

    参数:
        file_path (str): 文件路径
        collection_name (str): 集合名称，默认为 "rag"
        chunk_size (int): 分块大小，默认为 200
        chunk_overlap (int): 分块重叠长度，默认为 30

    返回:
        int: 成功保存的分块数量

    异常:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件类型或其他参数错误
    """
    try:
        # 步骤1：加载非结构化文本
        logger.info(f"开始提取文件内容: {file_path}")
        text = extract_text_auto(file_path)
        logger.info(f"文件内容提取完成，长度为{len(text)}个字符")
        
        # 检查文本是否为空
        if not text.strip():
            logger.warning(f"文件内容为空: {file_path}")
            return 0
        
        # 步骤2：将文本进行分块
        logger.info(f"开始进行文本分块 (chunk_size={chunk_size}, chunk_overlap={chunk_overlap})")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        chunks = splitter.split_text(text)
        logger.info(f"文本分块完成，共分为{len(chunks)}块")
        
        # 步骤3：为每个分块生成向量并保存入库
        success_count = 0
        for idx, chunk in enumerate(chunks):
            try:
                logger.info(f"正在保存第{idx+1}/{len(chunks)}块到向量数据库")
                save_text_to_db(chunk, collection_name=collection_name)
                success_count += 1
            except Exception as e:
                logger.error(f"保存第{idx+1}块失败: {str(e)}")
                # 继续处理下一块，不中断整个流程
        
        logger.info(f"文件 {file_path} 已完成入库，成功保存 {success_count}/{len(chunks)} 个分块")
        return success_count
        
    except FileNotFoundError:
        logger.error(f"文件不存在: {file_path}")
        raise
    except Exception as e:
        logger.error(f"文档入库失败: {file_path}, 错误: {str(e)}")
        raise

# 程序入口，如果直接运行本脚本，则执行入库操作（示例：入库‘红楼梦.txt’）
if __name__ == "__main__":
    doc_to_vectorstore('前端开发刘春达简历.docx')