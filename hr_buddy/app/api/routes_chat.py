import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from hr_buddy.app.api.auth import get_current_user

from hr_buddy.app.models.requests import ChatRequest
from hr_buddy.app.models.responses import ChatResponse
from hr_buddy.app.services.chat_service import ChatService


router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"]
)


chat_service = ChatService()


def session_key(user: dict, session_id: str | None) -> str | None:
    """Scope chat sessions to the user so one employee can't continue another's conversation."""

    return f"{user['id']}:{session_id}" if session_id else None


@router.post(
    "",
    response_model=ChatResponse
)
def chat(request: ChatRequest, user: dict = Depends(get_current_user)):

    result = chat_service.ask(
        request.question,
        rag_config=request.rag_config,
        llm_config=request.llm_config,
        document=request.document,
        session_id=session_key(user, request.session_id),
        user_id=user["id"],
        history=(
            [turn.model_dump() for turn in request.history]
            if request.history is not None
            else None
        ),
    )

    return ChatResponse(
        question=request.question,
        answer=result["answer"],
        sources=result["sources"],
        card=result["card"]
    )


@router.post("/stream")
def chat_stream(request: ChatRequest, user: dict = Depends(get_current_user)):
    """Stream the answer as newline-delimited JSON events."""

    events = chat_service.ask_stream(
        request.question,
        rag_config=request.rag_config,
        llm_config=request.llm_config,
        document=request.document,
        session_id=session_key(user, request.session_id),
        user_id=user["id"],
        history=(
            [turn.model_dump() for turn in request.history]
            if request.history is not None
            else None
        ),
    )

    def ndjson():
        try:
            for event in events:
                yield json.dumps(event) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"

    return StreamingResponse(
        ndjson(),
        media_type="application/x-ndjson"
    )
