# 导入sentence_transformers库中的SentenceTransformer类
from sentence_transformers import SentenceTransformer

# 导入chromadb库
import chromadb
# 从typing库导入List和Optional类型
from typing import List, Optional
# 导入logging库用于日志记录
import logging

# 导入llm模块（自定义的大模型API封装）
import llm

# 配置日志：设置日志等级为INFO，指定日志格式
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
# 获取当前模块的logger对象
logger = logging.getLogger(__name__)

# 默认集合名称，存储块的标签名
DEFAULT_COLLECTION_NAME = "rag"
# 默认嵌入模型名称
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
# 默认Chroma数据库路径
DEFAULT_DB_PATH = "./chroma_db"
# 默认检索返回文本块数目
DEFAULT_N_RESULTS = 3

# 全局SentenceTransformer模型实例（延迟初始化）
_model: Optional[SentenceTransformer] = None
# 全局ChromaDB客户端实例（延迟初始化）
_client: Optional[chromadb.PersistentClient] = None
# 全局ChromaDB集合实例（延迟初始化）
_collection: Optional[chromadb.Collection] = None

# 获取嵌入模型实例（单例模式，只有一个模型）
def _get_model() -> SentenceTransformer:
    # 声明使用全局变量_model
    global _model
    # 如果还没有实例化，则初始化模型
    if _model is None:
        # 打印加载模型信息
        logger.info(f"正在加载嵌入模型: {DEFAULT_MODEL_NAME}")
        _model = SentenceTransformer(DEFAULT_MODEL_NAME)
        # 加载完成
        logger.info("嵌入模型加载完成")
    # 返回模型实例
    return _model

# 获取ChromaDB客户端实例（单例模式）
def _get_client() -> chromadb.PersistentClient:
    # 声明全局变量_client
    global _client
    # 如果客户端还未初始化，则进行初始化
    if _client is None:
        # 打印初始化信息
        logger.info(f"正在初始化ChromaDB客户端，路径: {DEFAULT_DB_PATH}")
        _client = chromadb.PersistentClient(path=DEFAULT_DB_PATH)
        logger.info("ChromaDB客户端初始化完成")
    # 返回客户端实例
    return _client

# 获取或创建集合实例（单例模式），collection_name可指定集合名
def _get_collection(collection_name: str = DEFAULT_COLLECTION_NAME) -> chromadb.Collection:
    # 声明全局变量_collection
    global _collection
    # 如果集合还未初始化，则获取或创建集合
    if _collection is None:
        # 获取客户端
        client = _get_client()
        # 打印获取/创建集合信息
        logger.info(f"正在获取或创建集合: {collection_name}")
        _collection = client.get_or_create_collection(collection_name)
        logger.info(f"集合 '{collection_name}' 已准备就绪")
    # 返回集合实例
    return _collection

# 将query字符串转为embedding向量
def get_query_embedding(query: str) -> List[float]:
    """
    将查询文本转换为embedding向量
    
    参数:
        query (str): 查询文本
    
    返回:
        List[float]: embedding向量
    """
    # 打印debug信息，开始向量化
    logger.debug("正在将Query转为向量...")
    # 获取模型实例
    model = _get_model()
    # 调用模型将输入文本转为embedding，并转为list
    embedding = model.encode(query).tolist()
    # 打印向量化完成的debug信息
    logger.debug(f"Query向量化完成，向量维度: {len(embedding)}")
    # 返回embedding
    return embedding

# 向量检索，返回最相关的文本块列表
def retrieve_related_chunks(
    query_embedding: List[float],
    n_results: int = DEFAULT_N_RESULTS,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> List[str]:
    """
    向量检索，返回最相关的文本块列表
    
    参数:
        query_embedding (List[float]): 查询向量
        n_results (int): 返回的结果数量，默认为3
        collection_name (str): 集合名称，默认为 "rag"
    
    返回:
        List[str]: 最相关的文本块列表
    
    异常:
        ValueError: 未检索到相关内容
    """
    try:
        # 打印检索动作的日志
        logger.info(f"正在进行向量检索，返回最相关的{n_results}个文本块...")
        # 获取集合实例
        collection = _get_collection(collection_name)
        
        # 在指定集合中做向量相似度检索，n_results为最多返回的结果数
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 获取检索到的文档内容
        related_chunks = results.get("documents")
        
        # 检查是否检索到相关内容
        if not related_chunks or not related_chunks[0]:
            # 未检索到内容则打印警告并抛出异常
            logger.warning("未检索到相关内容，请先入库或检查数据库！")
            raise ValueError("未检索到相关内容，请先入库或检查数据库！")
        
        # 打印检索到的文本块数量
        logger.info(f"成功检索到{len(related_chunks[0])}个相关文本块")
        # 返回第一个结果list（按设计，一个query只查一个batch，取[0]即可）
        return related_chunks[0]
        
    except Exception as e:
        # 打印并抛出错误
        logger.error(f"向量检索失败: {str(e)}")
        raise

# RAG查询主函数：向量检索 + LLM生成答案
def query_rag(
    query: str,
    n_results: int = DEFAULT_N_RESULTS,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> str:
    """
    RAG查询主函数：向量检索 + LLM生成答案
    
    参数:
        query (str): 用户查询问题
        n_results (int): 检索的文档块数量，默认为3
        collection_name (str): 集合名称，默认为 "rag"
    
    返回:
        str: LLM生成的答案
    
    异常:
        ValueError: 检索失败或未找到相关内容
    """
    try:
        # 打印RAG查询开始日志
        logger.info(f"开始RAG查询: {query}")
        
        # 步骤1：将查询文本转为向量
        query_embedding = get_query_embedding(query)
        
        # 步骤2：基于query embedding做向量检索
        related_chunks = retrieve_related_chunks(
            query_embedding, n_results=n_results, collection_name=collection_name
        )
        
        # 步骤3：将检索到的文本块合并为上下文，拼接prompt
        context = "\n".join(related_chunks)
        prompt = f"已知信息：\n{context}\n\n请根据上述内容回答用户问题：{query}"
        # 打印构建的prompt长度
        logger.debug(f"Prompt已构建，长度: {len(prompt)}")
        
        # 步骤4：调用llm.invoke（大语言模型调用）生成最终答案
        logger.info("正在调用大模型生成答案...")
        answer = llm.invoke(prompt)
        # 打印答案生成完成
        logger.info("答案生成完成")
        
        # 返回模型生成的答案
        return answer
        
    except ValueError as e:
        # 捕获并打印检索失败相关的异常
        logger.error(f"RAG查询失败: {str(e)}")
        raise
    except Exception as e:
        # 捕获并打印所有其他异常
        logger.error(f"RAG查询过程中发生错误: {str(e)}")
        raise

# 主程序入口，支持直接命令行运行本脚本
if __name__ == "__main__":
    # 设定一个查询问题
    query = "刘春达有什么技能特长"
    logger.info(f"用户查询: {query}")
    
    try:
        # 进行RAG查询，设置n_results为10
        answer = query_rag(query, n_results=10)
        # 打印结果
        print("\n【答案】\n", answer)
    except ValueError as e:
        # 捕获未找到相关内容的错误，打印提示
        print(f"\n【错误】\n{str(e)}")
    except Exception as e:
        # 捕获程序异常，打印日志并提示
        logger.exception("程序执行失败")
        print(f"\n【错误】\n程序执行失败: {str(e)}")
