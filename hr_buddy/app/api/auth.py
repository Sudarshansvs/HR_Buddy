"""Who is calling: every protected route takes the user from the session token, never from the request body."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hr_buddy.app.hr_system import get_hr_system


bearer = HTTPBearer(auto_error=False)


def get_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:

    if credentials is None:
        raise HTTPException(status_code=401, detail="Please log in.")

    return credentials.credentials


def get_current_user(token: str = Depends(get_token)) -> dict:

    user = get_hr_system().user_for_token(token)

    if user is None:
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.")

    return user


def require_manager(user: dict = Depends(get_current_user)) -> dict:

    if not user["is_manager"]:
        raise HTTPException(status_code=403, detail="Only managers can do that.")

    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only HR admins can do that.")

    return user
