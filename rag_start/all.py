"""
all.py —— 一条龙学 RAG

主线只有四步（盯住这四步即可）：
  1. 切块 chunk
  2. 文本 → 向量 embedding，写入向量库
  3. 问题同样 embedding，按相似度取出相关原文
  4. 原文塞进 prompt，交给大模型生成答案

向量库负责「找相关段落」；大模型负责「组织回答」。拼起来就是 RAG。
"""

import os

import chromadb
from dotenv import load_dotenv
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from sentence_transformers import SentenceTransformer

load_dotenv(override=True)

# ---- 配置（改这里就够）----
DB_PATH = "./chroma_db"
COLLECTION = "rag"
EMBED_MODEL = "all-MiniLM-L6-v2"  # 384 维；入库/检索必须同一模型
CHUNK_SIZE, CHUNK_OVERLAP = 200, 30  # overlap：防止关键句被切断丢语义
N_RESULTS = 3

LLM_BASE = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
LLM_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("OPENAI_MODEL_NAME", "doubao-seed-2-0-mini-260428")

# 延迟加载：第一次用到时才初始化（模型较重）
_embedder = None
_collection = None
_llm = None


def get_embedder():
    """
    入参: 无
    返回: SentenceTransformer 模型对象（第一次会加载权重，之后复用）
    例:   get_embedder()  →  <SentenceTransformer(...)>   # 可调用 .encode
    """
    global _embedder
    if _embedder is None:
        print(f"加载嵌入模型: {EMBED_MODEL}")
        _embedder = SentenceTransformer(EMBED_MODEL, local_files_only=True)
    return _embedder


def get_collection():
    """
    集合 ≈ 一张向量表：存 documents（原文）+ embeddings（向量）+ ids。

    入参: 无（用顶部的 DB_PATH / COLLECTION）
    返回: Chroma Collection 对象
    例:   get_collection()  →  <Collection name=rag>
          之后可 .add(...) / .query(...)
    """
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=DB_PATH)
        _collection = client.get_or_create_collection(COLLECTION)
    return _collection


def get_llm():
    """
    入参: 无（用 .env 里的 OPENAI_*）
    返回: OpenAI 客户端
    例:   get_llm()  →  <OpenAI base_url=...api/v3>
    """
    global _llm
    if _llm is None:
        if not LLM_KEY:
            raise ValueError("请在 .env 设置 OPENAI_API_KEY")
        _llm = OpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
    return _llm


# ===========================================================================
# 0. 提取（非重点，一笔带过）
# ===========================================================================
def extract_text(path: str) -> str:
    """
    入参: path = "简历.docx"
    返回: 一整段纯文本 str
    例:   extract_text("简历.docx")
          →  "姓名：刘春达\\n技能：React、TypeScript\\n..."
    """
    ext = os.path.splitext(path)[-1].lower()
    if ext in {".txt", ".md"}:
        return open(path, encoding="utf-8", errors="ignore").read()
    if ext == ".docx":
        return "\n".join(p.text for p in Document(path).paragraphs if p.text.strip())
    raise ValueError(f"教学版仅支持 txt/md/docx，收到: {ext}")


# ===========================================================================
# 1. 分块 —— 块太长会混进无关信息，相似度召回变差
# ===========================================================================
def split_text(text: str) -> list[str]:
    """
    入参: text = "很长很长的文章……"（假设几千字）
    返回: list[str]，每段大约 CHUNK_SIZE 字符，相邻段有 CHUNK_OVERLAP 重叠
    例:   split_text("AAAA…AAAA" * 50)   # 很长的一串
          →  ["AAAA…(约200字)", "…重叠部分…AAAA…(约200字)", ...]
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    ).split_text(text)


# ===========================================================================
# 2. 向量化 + 入库
#    encode → list[float]；Chroma.add 同时放下「原文」和「向量」
# ===========================================================================
def embed(text: str) -> list[float]:
    """
    文字 → 向量。入库和提问都走这一步，才能在同一空间比距离。

    入参: text = "刘春达擅长前端"
    返回: list[float]，长度 384（本模型维度固定）
    例:   embed("刘春达擅长前端")
          →  [-0.017, 0.021, -0.003, ..., 0.015]   # 共 384 个数
    """
    return get_embedder().encode(text).tolist()


def save_chunk(text: str, source: str = "document") -> None:
    """
    写入一块。看懂 add 的四个字段就够：
      ids         唯一键（这里用 hash，相同文本不重复插）
      documents   原文 —— 检索命中后要还给 LLM
      embeddings  向量 —— 真正参与相似度计算
      metadatas   附加信息（可选，便于过滤）

    入参: text = "擅长 React 与 TypeScript", source = "简历.docx"
    返回: None（副作用：往向量库插入 1 行）
    例:   save_chunk("擅长 React", source="简历.docx")
          →  None
          库里多了一条大致等价于：
          {id: "123456", document: "擅长 React",
           embedding: [-0.01, 0.02, ...], metadata: {source: "简历.docx"}}
    """
    text = text.strip()
    if not text:
        return
    col = get_collection()
    text_id = str(abs(hash(text)))
    if col.get(ids=[text_id]).get("ids"):
        return  # 已存在则跳过
    col.add(
        ids=[text_id],
        documents=[text],
        embeddings=[embed(text)],
        metadatas=[{"source": source}],
    )


def ingest(path: str) -> int:
    """
    提取 → 分块 → 逐块入库。

    入参: path = "简历.docx"
    返回: int，成功处理的块数
    例:   ingest("简历.docx")  →  12
          # 表示这份简历被切成 12 块并写入 chroma_db
    """
    chunks = split_text(extract_text(path))
    print(f"分成 {len(chunks)} 块，写入 {DB_PATH} …")
    for i, chunk in enumerate(chunks, 1):
        save_chunk(chunk, source=path)
        print(f"  {i}/{len(chunks)}")
    return len(chunks)


# ===========================================================================
# 3. 检索 —— 问题也 embed，在同一向量空间找最近的原文块
# ===========================================================================
def retrieve(query: str, n: int = N_RESULTS) -> list[str]:
    """
    入参: query = "有什么技能特长", n = 3
    返回: list[str]，最相似的 n 段「原文」（不是向量）
    例:   retrieve("有什么技能特长", n=3)
          →  [
                "技能：React、TypeScript、Node.js",
                "负责过后台管理系统前端架构…",
                "熟悉 Webpack / Vite 构建…",
              ]
    """
    results = get_collection().query(query_embeddings=[embed(query)], n_results=n)
    # Chroma 支持一次多 query，所以 documents 是二维；取 [0] 即本条问题的结果
    docs = (results.get("documents") or [[]])[0]
    if not docs:
        raise ValueError("未检索到内容：请先入库，或检查 DB_PATH / COLLECTION")
    print(f"检索到 {len(docs)} 块")
    return docs


# ===========================================================================
# 4. 生成 —— 库只负责找原文；答案由 LLM 写
# ===========================================================================
def query_rag(question: str, n: int = N_RESULTS) -> str:
    """
    RAG 核心形状（记住这个模板）：
      已知信息：{retrieve 得到的原文}
      请根据上述内容回答：{用户问题}

    入参: question = "刘春达有什么技能特长", n = 3
    返回: str，大模型生成的答案
    例:   query_rag("刘春达有什么技能特长", n=3)
          →  "根据资料，刘春达擅长 React、TypeScript 等前端技术…"
    """
    context = "\n".join(retrieve(question, n=n))
    prompt = f"已知信息：\n{context}\n\n请根据上述内容回答用户问题：{question}"
    resp = get_llm().chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return resp.choices[0].message.content or ""


# ===========================================================================
# 入口：先入库再提问（第二次可注释掉 ingest）
# ===========================================================================
if __name__ == "__main__":
    demo_file = "前端开发刘春达简历.docx"
    question = "刘春达有什么技能特长"

    if os.path.exists(demo_file):
        print(f"【入库】{ingest(demo_file)} 块")
    else:
        print(f"找不到 {demo_file}，跳过入库")

    print("【答案】\n", query_rag(question, n=10))
