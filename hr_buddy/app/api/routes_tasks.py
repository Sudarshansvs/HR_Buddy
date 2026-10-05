from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hr_buddy.app.api.auth import get_current_user, require_manager

from hr_buddy.app.hr_system import HRSystemError, get_hr_system
from hr_buddy.app.hr_system.store import MIN_NOTICE_WORKING_DAYS, working_days
from hr_buddy.app.services.task_service import get_task_service


router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"]
)


class DecisionBody(BaseModel):

    approve: bool


def _run(action):
    """Turn refusals from the HR system into 400s with a readable message."""

    try:
        return {"message": action()}
    except HRSystemError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/actions/{action_id}/confirm")
def confirm_action(action_id: str, user: dict = Depends(get_current_user)):

    return _run(lambda: get_task_service().confirm_action(action_id, user["id"]))


@router.post("/actions/{action_id}/discard")
def discard_action(action_id: str, user: dict = Depends(get_current_user)):

    return _run(lambda: get_task_service().discard_action(action_id, user["id"]))


@router.post("/leave-requests/{request_id}/cancel")
def cancel_leave_request(request_id: int, user: dict = Depends(get_current_user)):

    return _run(lambda: get_task_service().cancel_request(user["id"], request_id))


@router.post("/leave-requests/{request_id}/decision")
def decide_leave_request(request_id: int, body: DecisionBody, user: dict = Depends(require_manager)):

    return _run(lambda: get_task_service().decide_request(user["id"], request_id, body.approve))


@router.get("/me/balance")
def leave_balance(user: dict = Depends(get_current_user)):

    return get_hr_system().leave_balance(user["id"])


@router.get("/me/requests")
def employee_requests(user: dict = Depends(get_current_user)):

    hr = get_hr_system()

    return {
        "leave_requests": hr.list_leave_requests(user["id"]),
        "tickets": hr.list_tickets(user["id"])
    }


@router.get("/team")
def manager_team(user: dict = Depends(require_manager)):
    """Everything the approvals page needs: pending requests with decision context, and recent decisions."""

    manager_id = user["id"]
    hr = get_hr_system()
    today = date.today()

    requests = hr.team_requests(manager_id)

    pending = []

    for request in sorted(
        (r for r in requests if r["status"] == "pending"),
        key=lambda r: r["start_date"]
    ):
        start = date.fromisoformat(request["start_date"])

        balance = hr.leave_balance(request["employee_id"], start.year)[request["leave_type"]]

        # Teammates already off (or asking to be off) on overlapping dates
        overlaps = [
            {
                "employee_name": other["employee_name"] or other["employee_id"],
                "start_date": other["start_date"],
                "end_date": other["end_date"],
                "status": other["status"]
            }
            for other in requests
            if other["id"] != request["id"]
            and other["employee_id"] != request["employee_id"]
            and other["status"] in ("pending", "approved")
            and other["start_date"] <= request["end_date"]
            and other["end_date"] >= request["start_date"]
        ]

        notice_days = working_days(today + timedelta(days=1), start - timedelta(days=1))

        pending.append(
            request | {
                # Pending days are already reserved, so this is what's left if approved
                "available_after": balance["available"],
                "entitled": balance["entitled"],
                "notice_working_days": notice_days,
                "short_notice": request["leave_type"] != "sick" and notice_days < MIN_NOTICE_WORKING_DAYS,
                "overlaps": overlaps
            }
        )

    decided = [
        r for r in requests
        if r["status"] in ("approved", "rejected") and r["decided_by"] == manager_id
    ]
    decided.sort(key=lambda r: r["decided_at"] or "", reverse=True)

    return {
        "manager_id": manager_id,
        "team_size": hr.team_size(manager_id),
        "pending": pending,
        "recent_decisions": decided[:20]
    }
