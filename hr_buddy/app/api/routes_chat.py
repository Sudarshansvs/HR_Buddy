from fastapi import APIRouter

from hr_buddy.app.models.requests import ChatRequest
from hr_buddy.app.models.responses import ChatResponse
from hr_buddy.app.services.chat_service import ChatService


router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"]
)


chat_service = ChatService()


@router.post(
    "",
    response_model=ChatResponse
)
def chat(request: ChatRequest):

    result = chat_service.ask(
        request.question
    )

    return ChatResponse(
        question=request.question,
        answer=result["answer"],
        sources=result["sources"]
    )