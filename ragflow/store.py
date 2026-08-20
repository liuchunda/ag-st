import chromadb
from pathlib import Path
from chromadb.config import Settings
from datetime import datetime,timezone
import logging
logger = logging.getLogger(__name__)
from models import RetrievalHit
class VectorStore:
    """ChromDB向量数据库的封装"""
    def __init__(self,db_path:str,collection_name:str,embedding_service:str)->None:
        self.db_path = db_path #保存数据库的存储路径
        self.collection_name = collection_name #保存集合的名称
        self.embedding_service = embedding_service #保存向量服务器的地址
        Path(self.db_path).mkdir(parents=True,exist_ok=True)
        self._client= chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(
                persist_directory=self.db_path,
                allow_reset=True, #允许重置数据库
                anonymized_telemetry=False, #匿名化遥测数据
            ),
        )
        #获取或创建集合
        self.collection = self._get_collection()


    def _get_collection(self)->chromadb.Collection:
        """获取集合"""
        return self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine", #指定HNSW索引使用的余弦相似度度量方式
                "description": "RAG向量数据库", #描述
                "create_at":datetime.now(timezone.utc).isoformat(), #创建时间
            }
        )
    def reset(self)->None:
        """重置数据库"""
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass#忽略错误
        self.collection = self._get_collection()
        logger.info(f"数据库重置成功: {self.collection_name}")
    
    @property
    def count(self)->int:
        """获取集合中的文档数量"""
        return self.collection.count()
    def upsert_chunks(self,chunks,batch_size=64)->None:
        """"批量向量化并写入，已经存在的ID则直接用upsert覆盖"""
        if not chunks:
            return 0
        written = 0
        for start in  range(0,len(chunks),batch_size): # 起始位置，结束为止，步长为batch_size
            batch = chunks[start:start+batch_size]
            embeddings = self.embedding_service.embed([chunk.content for chunk in batch])
            self.collection.upsert(
                ids=[chunk.id for chunk in batch],
                documents=[chunk.content for chunk in batch],
                metadatas=[chunk.metadata for chunk in batch],
                embeddings=embeddings,
            )
            written += len(batch)
            logger.info(f"写入进度: {written}/{len(chunks)}")
        return written
    
    def similarity_search(self,query:str,top_k:int=4,score_threshold:float=0.2,where=None)->list[RetrievalHit]:
        """相似度搜索"""
        query_vector = self.embedding_service.embed_query(query)
        n_results = min(top_k,self.count)
        kwargs = {
            "query_embeddings": [query_vector],#查询向量
            "n_results": n_results,#返回结果数量
            "include":["documents","metadatas","distances"],#返回结果包括文档、元数据和距离
        }
        if where:
            kwargs["where"] = where
        raw = self.collection.query(**kwargs)
        documents = (raw.get("documents") or [])[0] #获取文档
        metadatas = (raw.get("metadatas") or [])[0] #获取元数据
        distances = (raw.get("distances") or [])[0] #获取距离
        chunk_ids = (raw.get("ids") or [])[0] #获取ID
        scored = []
        for doc,meta,dist,chunk_id in zip(documents,metadatas,distances,chunk_ids):
            score = 1.0 - float(dist)
            scored.append((score,doc,meta,chunk_id))
        hits = []
        for score,doc,meta,chunk_id in scored:
            if score < score_threshold:
                continue
            # RetrievalHit
            hits.append(RetrievalHit(
                content=doc or "",
                source=str(meta.get("source","unknown")),
                chunk_id=str(chunk_id),
                score=round(score,4),
                metadata=dict(meta),
            ))
        hits.sort(key=lambda x: x.score,reverse=True)
        if not hits and scored:
            top = "，".join([str(chunk_id) for _,_,_,chunk_id in scored[:3]])
            logger.warning(f"相似度搜索结果为空，返回了相似度最高的{top_k}个结果: {top}")
        return hits


# raw = {
#     "ids": [
#         ["a1b2c3...", "d4e5f6...", "789abc..."]   # 第 1 个 query 的 id 列表
#     ],
#     "documents": [
#         [
#             "司龄 1-10 年：每年 5 天带薪年假...",
#             "须提前至少 3 个工作日申请...",
#             "## 2. 考勤管理\n标准工作时间...",
#         ]
#     ],
#     "metadatas": [
#         [
#             {"source": "handbook.md", "chunk_index": 2, "char_len": 380},
#             {"source": "handbook.md", "chunk_index": 1, "char_len": 420},
#             {"source": "handbook.md", "chunk_index": 0, "char_len": 350},
#         ]
#     ],
#     "distances": [
#         [0.15, 0.28, 0.45]   # 余弦距离，越小越相似
#     ],
#     # 若 include 里写了 "embeddings"，还会有 embeddings: [[...], ...]
# }