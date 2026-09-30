from pydantic import BaseModel


class Source(BaseModel):

    document: str

    page: int | None = None

    content: str

    score: float | None = None


class ChatResponse(BaseModel):

    question: str

    answer: str

    sources: list[Source]