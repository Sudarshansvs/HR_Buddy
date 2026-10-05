from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hr_buddy.app.api.auth import require_admin
from hr_buddy.app.hr_system import HRSystemError, get_hr_system


# Every route here is for HR admins only
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)]
)


class NewEmployee(BaseModel):

    employee_id: str

    name: str = ""

    manager_id: str | None = None

    role: str = "employee"

    password: str


class PasswordBody(BaseModel):

    password: str


class TicketStatusBody(BaseModel):

    status: str


def _run(action):

    try:
        return action()
    except HRSystemError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/employees")
def list_employees():

    return get_hr_system().list_employees()


@router.post("/employees")
def create_employee(body: NewEmployee):

    return _run(lambda: get_hr_system().create_employee(
        body.employee_id, body.name, body.manager_id, body.role, body.password
    ))


@router.post("/employees/{employee_id}/password")
def reset_password(employee_id: str, body: PasswordBody):

    _run(lambda: get_hr_system().set_password(employee_id, body.password))

    return {"message": f"Password reset for {employee_id}. They have been signed out."}


@router.get("/tickets")
def all_tickets():

    return get_hr_system().all_tickets()


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, body: TicketStatusBody):

    return _run(lambda: get_hr_system().set_ticket_status(ticket_id, body.status))


@router.get("/leave-requests")
def all_leave_requests():

    return get_hr_system().all_leave_requests()
