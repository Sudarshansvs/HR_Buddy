from pydantic import BaseModel, Field


class RAGConfig(BaseModel):
    """RAG configuration parameters"""

    chunk_size: int = Field(
        default=500,
        ge=50,
        le=2000,
        description="Size of text chunks for RAG"
    )

    chunk_overlap: int = Field(
        default=100,
        ge=0,
        le=500,
        description="Overlap between chunks"
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top results to retrieve"
    )


class ChatRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1,
        description="HR question"
    )

    session_id: str | None = None

    rag_config: RAGConfig | None = Field(
        default=None,
        description="Optional RAG configuration"
    )