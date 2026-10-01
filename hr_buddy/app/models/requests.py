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


class LLMConfig(BaseModel):
    """LLM tuning parameters"""

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Controls randomness: 0=deterministic, 2=very random"
    )

    max_tokens: int = Field(
        default=500,
        ge=100,
        le=4000,
        description="Maximum length of the response"
    )

    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Cumulative probability for nucleus sampling"
    )

    frequency_penalty: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Penalizes repeated tokens"
    )

    presence_penalty: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Penalizes tokens based on appearance"
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

    llm_config: LLMConfig | None = Field(
        default=None,
        description="Optional LLM tuning configuration"
    )

    # Optional: if provided, limit retrieval to this document only
    document: str | None = Field(
        default=None,
        description="Optional document filename to restrict the search to"
    )