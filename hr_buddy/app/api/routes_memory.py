from fastapi import APIRouter, Depends, HTTPException

from hr_buddy.app.api.auth import get_current_user
from hr_buddy.app.api.routes_chat import session_key
from hr_buddy.app.memory import (
    get_long_term_memory,
    get_short_term_memory
)


# Everything here acts on the logged-in employee's own memory
router = APIRouter(
    prefix="/api/v1/memory/me",
    tags=["Memory"]
)


@router.get("")
def list_long_term_memories(user: dict = Depends(get_current_user)):

    return {
        "user_id": user["id"],
        "memories": get_long_term_memory().list(user["id"])
    }


@router.delete("")
def clear_long_term_memories(user: dict = Depends(get_current_user)):

    get_long_term_memory().clear(user["id"])

    return {"message": "Long-term memory cleared"}


@router.delete("/{memory_id}")
def delete_long_term_memory(memory_id: str, user: dict = Depends(get_current_user)):

    if not get_long_term_memory().delete(user["id"], memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"message": "Memory deleted"}


@router.get("/sessions/{session_id}")
def get_short_term_memory_turns(session_id: str, user: dict = Depends(get_current_user)):

    return {
        "session_id": session_id,
        "turns": get_short_term_memory().get(session_key(user, session_id))
    }


@router.delete("/sessions/{session_id}")
def clear_short_term_memory(session_id: str, user: dict = Depends(get_current_user)):

    get_short_term_memory().clear(session_key(user, session_id))

    return {"message": "Conversation memory cleared"}
