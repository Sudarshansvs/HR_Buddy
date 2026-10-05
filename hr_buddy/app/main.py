from fastapi import FastAPI

from hr_buddy.app.api.routes_chat import router as chat_router
from hr_buddy.app.api.routes_health import router as health_router
from hr_buddy.app.api.routes_documents import (
    router as document_router
)
from hr_buddy.app.api.routes_memory import (
    router as memory_router
)
from hr_buddy.app.api.routes_tasks import (
    router as task_router
)
from hr_buddy.app.api.routes_auth import (
    router as auth_router
)
from hr_buddy.app.api.routes_admin import (
    router as admin_router
)
from hr_buddy.app.core.config import settings
from hr_buddy.app.core.logging import (
    setup_logging
)


setup_logging()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "GenAI powered HR Assistant"
    ),
    version="1.0.0"
)


app.include_router(
    health_router
)

app.include_router(
    chat_router
)

app.include_router(
    document_router
)

app.include_router(
    memory_router
)

app.include_router(
    task_router
)

app.include_router(
    auth_router
)

app.include_router(
    admin_router
)


@app.get("/")
def root():

    return {
        "application": settings.APP_NAME,
        "status": "running"
    }