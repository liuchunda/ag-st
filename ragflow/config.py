import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv(override=True)
@dataclass(frozen=True)
class RAGConfig:
    """RAG运行时配置"""
    db_path:str = './chroma_db'
    collection_name:str="rag"
    embedding_model:str="paraphrase-multilingual-MiniLM-L12-v2"
    chunk_size:int=500 #分块大小
    chunk_overlap:int=80 #分块重叠
    top_k:int=5# 检索返回相似的文档数量
    score_threshold:float=0.5# 相似度得分阈值
    max_content_chars:int=6000# 上下文最大的字符数
    openai_base_url: str = "https://api.deepseek.com"
    openai_api_key:str=os.getenv("RAG_API_KEY")
    openai_model:str="deepseek-v4-flash"
    temperature:float=0.2 # 生成温度参数
    @classmethod
    def from_env(cls):
        """从环境变量中加载配置"""
        return cls(
            db_path=os.getenv("DB_PATH",cls.db_path),
            collection_name=os.getenv("RAG_COLLECTION_NAME",cls.collection_name),
            embedding_model=os.getenv("RAG_EMBEDDING_MODEL",cls.embedding_model),
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE",cls.chunk_size)),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP",cls.chunk_overlap)),
            top_k=int(os.getenv("TOP_K",cls.top_k)),
            score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD",cls.score_threshold)),
            max_content_chars=int(os.getenv("RAG_MAX_CONTENT_CHARS",cls.max_content_chars)),
            openai_base_url=os.getenv("OPENAI_BASE_URL",cls.openai_base_url),
            openai_api_key=os.getenv("RAG_API_KEY",cls.openai_api_key),
            openai_model=os.getenv("RAG_OPENAI_MODEL",cls.openai_model),
            temperature=float(os.getenv("TEMPERATURE",cls.temperature)),
        )