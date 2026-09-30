from fastapi import APIRouter

from hr_buddy.app.core.config import settings


router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("")
def health():

    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "model": settings.LLM_MODEL
    }