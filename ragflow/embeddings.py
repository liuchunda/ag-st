import logging
logger = logging.getLogger(__name__)
from sentence_transformers import SentenceTransformer# sentenceTransformer是sentence-transformers库中的一个模型，用于将文本转换成向量
class EmbeddingService:
    def __init__(self,model_name:str)->None:
        self.model_name = model_name
        self._model = None
    
    def _get_model(self):
        if self._model is None:
            logger.info(f"加载模型 {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"模型 {self.model_name} 加载成功")
        return self._model
    
    def embed(self,texts):
        model = self._get_model()
        batch = [texts] if isinstance(texts,str) else texts
        vectors = model.encode(
            batch,
            show_progress_bar = True,#显示进度条
            normalize_embeddings = True,#归一化向量
        )
        return [v.tolist() for v in vectors]
    # 定义单个查询文本向量化的方法，接收字符串，返回此字符串对应的向量
    def embed_query(self, query):
        return self.embed(query)[0]