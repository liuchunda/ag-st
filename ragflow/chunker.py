from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import DocumentChunk
import hashlib
import logging
logger = logging.getLogger(__name__)
class TextChunker:
    def __init__(self,chunk_size:int=500,chunk_overlap:int=80):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,#分块大小
            chunk_overlap=chunk_overlap,#分块重叠长度
            length_function=len,#使用内置的len函数计算文本长度
            is_separator_regex=False,#是否使用正则表达式分割
            separators=[
                # 优先按空行（段落）切分
                "\n\n",
                # 其次按换行切分
                "\n",
                # 按中文句号切分
                "。",
                # 按中文感叹号切分
                "！",
                # 按中文问号切分
                "？",
                # 按中文分号切分
                "；",
                # 按英文句号加空格切分
                ". ",
                # 按英文感叹号加空格切分
                "! ",
                # 按英文问号加空格切分
                "? ",
                # 按空格切分
                " ",
                # 最后按字符强制切分
                "",
                # 结束分隔符列表
            ]
        )
    
    def split(self,text:str,source:str)->list[str]:
        raw_chunks = self.splitter.split_text(text)
        chunks = []
        for idx,chunk in enumerate(raw_chunks):
            chunk_id = self._stable_id(source,idx,chunk)
            chunks.append(DocumentChunk(
                id=chunk_id,
                content=chunk,
                source=source,
                chunk_index=idx,
                metadata={
                    "source": source,
                    "chunk_index": idx,
                    "char_len": len(chunk),
                },
            ))
        logger.info(f"分块完成: {len(chunks)} 块，源文件: {source}")
        return chunks

    @staticmethod
    def _stable_id(source:str,idx:int,content:str)->str:
        """"生成稳定的ID"""
        digest = hashlib.sha256(
            f"{source}-{idx}-{content}".encode("utf-8")
        ).hexdigest()
        return digest[:32]
