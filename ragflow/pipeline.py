from config import RAGConfig
from loader import DocumentLoader
from embeddings import EmbeddingService
from store import VectorStore
from chunker import TextChunker
from llm import LLMClient
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
from models import RAGAnswer
class RAGFlowPipeline:
    """RAG主流程编排器"""
    def __init__(self,config=None):
        self.config = config or RAGConfig().form_env()
        self.loader = DocumentLoader()
        self.embedding_service = EmbeddingService(self.config.embedding_model)
        self.store = VectorStore(
            db_path=self.config.db_path,
            collection_name=self.config.collection_name,
            embedding_service=self.embedding_service,
        )
        self.chunker = TextChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self.llm = LLMClient(self.config)


    # 导入文件
    def ingest_file(self, file_path):
        # 将输入的路径转为绝对路径对象
        path = Path(file_path).resolve()
        # 如果此路径不指向一个具体存在的文件
        if not path.is_file():
            raise ValueError(f"请指定文件路径:{path}")
        # 调用文档加载器解析文件内容为文本
        text = self.loader.load(path)
        # 判断清洗后的文件是否为空
        if not text.strip():
            # 如果是空文件则
            # # 返回0，表示未提取到有效的内容
            return 0
        # 正常这里不需要重置集合，为了我们测试方便，不受历史数据影响，所以在这清一下数据库
        self.store.reset()
        # 调用文本分块器将文本分为小的文本块列表
        chunks = self.chunker.split(text, source=str(path.name))
        # 调用向量存储实例将文本块列表插入到向量数据库中
        n = self.store.upsert_chunks(chunks)
        logger.info("入库成功:%s -> %d chunks", path.name, n)
        return n

    # 检索
    def retrieve(self, question, top_k=None):
        return self.store.similarity_search(
            query=question,  # 传入查询的文本
            top_k=top_k
            or self.config.top_k,  # 传入返回数量，未指定时回退为配置中的top_k
            score_threshold=self.config.score_threshold,  # 传入配置中的相似度分数的阈值
        )

    # 构建提示词
    def build_prompt(self, question, hits):
        if not hits:
            return (
                "参数资料:无\n\n"
                f"用户问题:{question}\n\n"
                "请说明知识库中暂无相关信息"
            )
        # 初始化用于拼接参考资料片段的列表
        parts = []
        # 初始化已经使用的上下文字符数计数器
        # used只是参考资料的长度
        used = 0
        for index, hit in enumerate(hits, start=1):
            # 构建单条参考资料文本块，包含序号来源相似度与正文
            block = (
                f"[{index}]来源：{hit.source} | 相似度:{hit.score:.4f}\n"
                f"{hit.content}\n"
            )
            # 判断追加当前文本块之后是否超出了最大的上下文字符数限制
            if used + len(block) > self.config.max_content_chars:
                # 如果超过了限制则停止追加更多的命中结果
                break
            # 将当前的文本块添加到参考资料列表中
            parts.append(block)
            # 累加当前的文本块占用的字符数
            used += len(block)
        context = "\n".join(parts)
        return (
            "以下是从知识库中检索到的参考资料:\n"
            f"{context}\n"
            f"用户问题:{question}\n"
            "请基于上述参考资料作答."
        )

    # 定义问答方法，接收问题文本与可选的返回数量
    def ask(self, question, top_k=None):
        question = question.strip()
        if not question:
            raise ValueError("问题不能为空")
        logger.info("开始RAG问答:%s", question)
        # 调用检索方法获取与问题最相关的命中结果
        hits = self.retrieve(question, top_k=top_k)
        # 根据问题和检索命中的结果构建提示词
        prompt = self.build_prompt(question, hits)
        if not prompt:
            answer = "根据现有的知识库无法确定相关的答案，请补充文档后重试"
        else:
            answer = self.llm.generate_response(prompt)
        result = RAGAnswer(
            question=question,
            answer=answer,
            citations=hits,
            model=self.config.openai_model,
            prompt_preview=prompt[:500] + ("..." if len(prompt) > 500 else ""),
        )
        logger.info("回答完成:citations=%d", len(hits))
        return result
