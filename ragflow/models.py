from dataclasses import asdict, dataclass, field
from this import d

@dataclass
class RetrievalHit:
    content: str
    source: str
    chunk_id: str
    score: float
    metadata: dict

@dataclass
class DocumentChunk:
    id: str
    content: str
    source: str
    chunk_index: int
    metadata: dict

@dataclass
class RAGAnswer:
    question: str
    answer: str
    citations: list[RetrievalHit]
    model: str
    prompt_preview: str