# 导入 chromadb 库
import chromadb
# 导入 Optional 类型，用于类型标注
from typing import Optional
# 导入 logging 模块，用于日志记录
import logging

# 导入 sentence_transformers 库中的 SentenceTransformer 类
from sentence_transformers import SentenceTransformer

# 获取当前模块的 logger 实例
logger = logging.getLogger(__name__)

# 设置默认的集合名称
DEFAULT_COLLECTION_NAME = "rag"
# 设置默认的模型名称
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
# 设置默认的数据库文件路径
DEFAULT_DB_PATH = "./chroma_db"

# 定义全局变量 _model，用于存放 SentenceTransformer 实例，初始为 None
_model: Optional[SentenceTransformer] = None
# 定义全局变量 _client，用于存放 chromadb 的 PersistentClient 实例，初始为 None
_client: Optional[chromadb.PersistentClient] = None

# 定义获取嵌入模型的内部方法，如果未初始化则进行加载
def _get_model() -> SentenceTransformer:
    """
    获取嵌入模型实例（单例模式）
    返回:
        SentenceTransformer: 嵌入模型实例
    """
    # 声明使用全局变量 _model
    global _model
    # 如果 _model 尚未实例化，则进行初始化
    if _model is None:
        # 记录开始加载模型的日志
        logger.info(f"正在加载嵌入模型: {DEFAULT_MODEL_NAME}")
        # 加载 SentenceTransformer 模型
        _model = SentenceTransformer(DEFAULT_MODEL_NAME,local_files_only = True)
        # 记录模型加载完成的日志
        logger.info("嵌入模型加载完成")
    # 返回模型实例
    return _model

# 定义获取 ChromaDB 客户端的内部方法，如果未初始化则进行加载
def _get_client() -> chromadb.PersistentClient:
    """
    获取ChromaDB客户端实例（单例模式）
    返回:
        chromadb.PersistentClient: 客户端实例
    """
    # 声明使用全局变量 _client
    global _client
    # 如果 _client 尚未实例化，则进行初始化
    if _client is None:
        # 记录开始初始化客户端的日志，并输出路径信息
        logger.info(f"正在初始化ChromaDB客户端，路径: {DEFAULT_DB_PATH}")
        # 初始化 PersistentClient 实例
        _client = chromadb.PersistentClient(path=DEFAULT_DB_PATH)
        # 记录客户端初始化完成的日志
        logger.info("ChromaDB客户端初始化完成")
    # 返回客户端实例
    return _client

# 定义将文本保存到 ChromaDB 的函数
def save_text_to_db(text: str, collection_name: str = DEFAULT_COLLECTION_NAME, source: Optional[str] = None) -> str:
    """
    将文本保存到ChromaDB指定集合中，使用sentence_transformers生成embedding。

    参数:
        text (str): 要保存的文本
        collection_name (str): 集合名称，默认为 "rag"
        source (str, optional): 数据来源标识，默认为 "document"

    返回:
        str: 保存的文本ID

    异常:
        Exception: 保存失败
    """
    try:
        # 如果文本为空或者全是空白字符，直接记录警告并返回空字符串
        if not text or not text.strip():
            logger.warning("尝试保存空文本，已跳过")
            return ""

        # 获取全局模型实例
        model = _get_model()
        # 获取全局客户端实例
        client = _get_client()

        # 获取指定名称的集合，如果集合不存在则自动创建
        collection = client.get_or_create_collection(collection_name)
        # 使用文本内容的哈希值生成唯一的文本ID（转为正整数再转为字符串）
        text_id = str(abs(hash(text)))

        # 检查数据库中是否已经存在相同的ID
        existing = collection.get(ids=[text_id])
        # 如果存在该ID，说明相同内容已保存，无需重复保存
        if existing and existing.get("ids"):
            logger.debug(f"文本已存在，跳过保存，id={text_id}")
            return text_id

        # 生成文本的 embedding，模型处理结果为 ndarray，通过tolist 转换为列表
        embedding = model.encode([text])[0].tolist()

        # 向集合中添加文本、元数据、ID 以及 embedding（均为单元素列表）
        collection.add(
            documents=[text],
            metadatas=[{"source": source or "document"}],
            ids=[text_id],
            embeddings=[embedding],
        )

        # 记录成功保存的调试日志，包含文本id和集合名称
        logger.debug(f"文本已保存到ChromaDB，id={text_id}, collection={collection_name}")
        # 返回本次保存的文本ID
        return text_id

    # 捕捉整个保存过程中的异常
    except Exception as e:
        # 记录错误日志并输出异常信息
        logger.error(f"保存文本到数据库失败: {str(e)}")
        # 抛出异常
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    text_id = save_text_to_db("这是一段测试文本", source="test")
    print("保存成功，id =", text_id)