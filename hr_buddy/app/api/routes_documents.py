from fastapi import APIRouter

from hr_buddy.app.services.chat_service import ChatService


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"]
)


@router.post("/reload")
def reload_documents():

    # In a later version this will trigger
    # a proper ingestion pipeline.

    return {
        "message": (
            "Document reload endpoint "
            "is available."
        )
    }