import threading
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hr_buddy.app.api.auth import get_current_user, get_token
from hr_buddy.app.hr_system import get_hr_system


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Auth"]
)


# Slow down password guessing: this many failures per ID locks it for the window
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60

_failures: dict[str, list[float]] = {}
_failures_lock = threading.Lock()


class LoginBody(BaseModel):

    employee_id: str

    password: str


def _recent_failures(employee_id: str) -> list[float]:

    cutoff = time.time() - LOCKOUT_SECONDS

    with _failures_lock:
        _failures[employee_id] = [t for t in _failures.get(employee_id, []) if t > cutoff]
        return _failures[employee_id]


@router.post("/login")
def login(body: LoginBody):

    employee_id = body.employee_id.strip()

    if len(_recent_failures(employee_id)) >= MAX_FAILED_LOGINS:
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Please try again in 15 minutes."
        )

    hr = get_hr_system()
    token = hr.login(employee_id, body.password)

    if token is None:
        with _failures_lock:
            _failures.setdefault(employee_id, []).append(time.time())
        # Same message whether the ID or the password was wrong
        raise HTTPException(status_code=401, detail="Invalid employee ID or password.")

    with _failures_lock:
        _failures.pop(employee_id, None)

    return {"token": token, "user": hr.get_employee(employee_id)}


@router.post("/logout")
def logout(token: str = Depends(get_token)):

    get_hr_system().logout(token)

    return {"message": "Logged out"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):

    return user
