"""Task handling: leave, requests, approvals and tickets against the HR system.

Nothing that changes data happens from chat text alone. Chat replies carry a
"card" whose buttons call the task endpoints, so every change is an explicit
click: Confirm/Discard for new leave requests and tickets, and the
Cancel/Approve/Reject buttons on specific requests. Button bodies carry no
identity: the endpoints act as the logged-in user.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from hr_buddy.app.hr_system import HRSystem, HRSystemError, get_hr_system
from hr_buddy.app.services.llm_service import LLMService
from hr_buddy.app.tasks.parsing import (
    has_explicit_date,
    is_cancel,
    leave_type_from,
    simple_dates_from,
    ticket_category_from
)


logger = logging.getLogger(__name__)


TASK_INTENTS = {
    "apply_leave",
    "leave_balance",
    "my_requests",
    "cancel_request",
    "approvals",
    "raise_ticket",
}

# Unconfirmed actions and half-filled drafts are dropped after this long
PENDING_TTL_SECONDS = 30 * 60

API_PREFIX = "/api/v1/tasks"

STATUS_ICONS = {
    "pending": "🟡 pending",
    "approved": "🟢 approved",
    "rejected": "🔴 rejected",
    "cancelled": "⚪ cancelled",
    "open": "🟡 open",
}


@dataclass
class TaskResult:

    text: str

    card: dict | None = None


@dataclass
class _Pending:

    user_id: str

    kind: str

    params: dict = field(default_factory=dict)

    created: float = field(default_factory=time.time)

    def expired(self) -> bool:
        return time.time() - self.created > PENDING_TTL_SECONDS


def _format_dates(start: date, end: date) -> str:

    if start == end:
        return f"{start:%a %d %b %Y}"

    return f"{start:%a %d %b} → {end:%a %d %b %Y}"


def _request_dates(request: dict) -> str:

    return _format_dates(
        date.fromisoformat(request["start_date"]),
        date.fromisoformat(request["end_date"])
    )


def _button(label: str, path: str, body: dict, primary: bool = False) -> dict:

    return {
        "label": label,
        "path": f"{API_PREFIX}{path}",
        "body": body,
        "primary": primary
    }


class TaskService:

    def __init__(self, llm: LLMService = None, hr: HRSystem = None):

        self.llm = llm or LLMService()

        self.hr = hr or get_hr_system()

        # session_id -> draft being filled in over several messages
        self._drafts: dict[str, _Pending] = {}

        # action_id -> action waiting for the employee to confirm
        self._actions: dict[str, _Pending] = {}

        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Entry points from chat
    # ------------------------------------------------------------------

    def handle(self, intent: str, question: str, user_id: str | None, session_id: str | None, today: date = None) -> TaskResult:

        if not user_id:
            return TaskResult(
                "To do that I need to know who you are. Please log in and ask again."
            )

        today = today or date.today()

        handlers = {
            "apply_leave": self._apply_leave,
            "leave_balance": self._leave_balance,
            "my_requests": self._my_requests,
            "cancel_request": self._cancel_request,
            "approvals": self._approvals,
            "raise_ticket": self._raise_ticket,
        }

        return handlers[intent](question, user_id, session_id, today)

    def continue_draft(self, question: str, user_id: str | None, session_id: str | None, today: date = None) -> TaskResult | None:
        """Feed a message into an unfinished task. None means the message isn't part of it."""

        draft = self._take_draft(session_id)

        if not draft or draft.user_id != user_id:
            return None

        if is_cancel(question):
            return TaskResult("Okay, I've stopped that. Nothing was submitted.")

        today = today or date.today()

        if draft.kind == "apply_leave":
            details = self._leave_details(question, today)
            if not details:
                # Nothing about the leave in this message; treat it as a new topic
                return None
            return self._apply_leave(question, user_id, session_id, today, draft.params | details)

        if draft.kind == "raise_ticket":
            return self._raise_ticket(question, user_id, session_id, today, draft.params)

        return None

    # ------------------------------------------------------------------
    # Entry points from the card buttons
    # ------------------------------------------------------------------

    def confirm_action(self, action_id: str, user_id: str, today: date = None) -> str:

        action = self._take_action(action_id, user_id)

        if action.kind == "apply_leave":
            params = action.params
            request = self.hr.create_leave_request(
                user_id, params["leave_type"], params["start"], params["end"], today
            )
            return (
                f"Submitted **LR-{request['id']}**: {request['leave_type']} leave, "
                f"{_request_dates(request)} ({request['days']} day(s)). "
                "It's pending your manager's approval."
            )

        if action.kind == "raise_ticket":
            ticket = self.hr.create_ticket(
                user_id, action.params["category"], action.params["description"]
            )
            return f"Raised ticket **TKT-{ticket['id']}**. HR Operations will follow up."

        raise HRSystemError("Unknown action.")

    def discard_action(self, action_id: str, user_id: str) -> str:

        self._take_action(action_id, user_id)

        return "Discarded. Nothing was submitted."

    def cancel_request(self, user_id: str, request_id: int, today: date = None) -> str:

        request = self.hr.cancel_leave_request(user_id, request_id, today)

        return f"Cancelled **LR-{request['id']}** ({_request_dates(request)})."

    def decide_request(self, manager_id: str, request_id: int, approve: bool) -> str:

        request = self.hr.decide_leave_request(manager_id, request_id, approve)

        return f"{'Approved' if approve else 'Rejected'} **LR-{request['id']}**."

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _leave_details(self, question: str, today: date) -> dict:
        """Leave type and dates found in a message, if any."""

        details = {}

        leave_type = leave_type_from(question)
        if leave_type:
            details["leave_type"] = leave_type

        if has_explicit_date(question):
            dates = self.llm.extract_leave_dates(question, today)
        else:
            dates = simple_dates_from(question, today)

        if dates:
            details["start"], details["end"] = dates

        return details

    def _apply_leave(self, question, user_id, session_id, today, known: dict = None) -> TaskResult:

        params = known if known is not None else self._leave_details(question, today)

        missing = [
            label
            for key, label in [("leave_type", "which type of leave (annual, casual or sick)"),
                               ("start", "which date(s)")]
            if key not in params
        ]

        if missing:
            self._save_draft(session_id, _Pending(user_id, "apply_leave", params))
            return TaskResult(f"Sure, I can apply for leave. Please tell me {' and '.join(missing)}.")

        try:
            check = self.hr.check_leave(
                user_id, params["leave_type"], params["start"], params["end"], today
            )
        except HRSystemError as error:
            # Keep the leave type so the employee only has to give new dates
            retry = {"leave_type": params["leave_type"]}
            self._save_draft(session_id, _Pending(user_id, "apply_leave", retry))
            return TaskResult(f"I can't submit that: {error} Please give different dates.")

        action_id = self._save_action(_Pending(user_id, "apply_leave", params))

        rows = [
            ["Type", f"{params['leave_type'].capitalize()} leave"],
            ["Dates", _format_dates(params["start"], params["end"])],
            ["Working days", str(check["days"])],
        ]

        return TaskResult(
            "Here's the leave request. Please check the dates and confirm.",
            self._confirm_card("Leave request", rows, check["warnings"], action_id)
        )

    def _raise_ticket(self, question, user_id, session_id, today, known: dict = None) -> TaskResult:

        if known is None and len(question.split()) < 5:
            # "raise a ticket" alone doesn't say what the issue is
            self._save_draft(session_id, _Pending(user_id, "raise_ticket"))
            return TaskResult("Sure. What's the issue you'd like HR to look into?")

        params = {
            "category": ticket_category_from(question),
            "description": question.strip()
        }

        action_id = self._save_action(_Pending(user_id, "raise_ticket", params))

        rows = [
            ["Category", params["category"].replace("_", " ").capitalize()],
            ["Issue", params["description"]],
        ]

        return TaskResult(
            "I'll raise this with HR Operations. Please confirm.",
            self._confirm_card("HR ticket", rows, [], action_id)
        )

    def _leave_balance(self, question, user_id, session_id, today) -> TaskResult:

        balance = self.hr.leave_balance(user_id, today.year)

        lines = [
            f"Your leave balance for {today.year}:",
            "",
            "| Type | Entitled | Used | Pending | Available |",
            "|---|---|---|---|---|",
        ]

        for leave_type, values in balance.items():
            lines.append(
                f"| {leave_type.capitalize()} | {values['entitled']} | {values['used']} "
                f"| {values['pending']} | **{values['available']}** |"
            )

        return TaskResult("\n".join(lines))

    def _my_requests(self, question, user_id, session_id, today) -> TaskResult:

        requests = self.hr.list_leave_requests(user_id)
        tickets = self.hr.list_tickets(user_id)

        if not requests and not tickets:
            return TaskResult("You don't have any leave requests or tickets yet.")

        lines = []

        if requests:
            lines += [
                "**Leave requests**",
                "",
                "| ID | Type | Dates | Days | Status |",
                "|---|---|---|---|---|",
            ]
            lines += [
                f"| LR-{r['id']} | {r['leave_type'].capitalize()} | {_request_dates(r)} "
                f"| {r['days']} | {STATUS_ICONS.get(r['status'], r['status'])} |"
                for r in requests
            ]

        if tickets:
            lines += [
                "",
                "**Tickets**",
                "",
                "| ID | Category | Issue | Status |",
                "|---|---|---|---|",
            ]
            lines += [
                f"| TKT-{t['id']} | {t['category'].replace('_', ' ').capitalize()} "
                f"| {t['description'][:60]} | {STATUS_ICONS.get(t['status'], t['status'])} |"
                for t in tickets
            ]

        return TaskResult("\n".join(lines))

    def _cancel_request(self, question, user_id, session_id, today) -> TaskResult:

        requests = self.hr.cancellable_requests(user_id, today)

        if not requests:
            return TaskResult("You don't have any upcoming leave requests that can be cancelled.")

        items = [
            {
                "heading": f"LR-{r['id']} · {r['leave_type'].capitalize()} leave",
                "rows": [
                    ["Dates", _request_dates(r)],
                    ["Status", STATUS_ICONS.get(r["status"], r["status"])],
                ],
                "buttons": [
                    _button(
                        "Cancel this request",
                        f"/leave-requests/{r['id']}/cancel",
                        {}
                    )
                ]
            }
            for r in requests
        ]

        return TaskResult(
            "Which request would you like to cancel?",
            {"title": "Your upcoming leave", "items": items}
        )

    def _approvals(self, question, user_id, session_id, today) -> TaskResult:

        requests = self.hr.pending_approvals(user_id)

        if not requests:
            return TaskResult("There are no leave requests waiting for your approval.")

        items = []

        for r in requests:
            items.append(
                {
                    "heading": f"LR-{r['id']} · {r['employee_name'] or r['employee_id']}",
                    "rows": [
                        ["Type", f"{r['leave_type'].capitalize()} leave"],
                        ["Dates", _request_dates(r)],
                        ["Working days", str(r["days"])],
                    ],
                    "buttons": [
                        _button("Approve", f"/leave-requests/{r['id']}/decision", {"approve": True}, primary=True),
                        _button("Reject", f"/leave-requests/{r['id']}/decision", {"approve": False}),
                    ]
                }
            )

        return TaskResult(
            f"You have {len(requests)} request(s) waiting for your approval.",
            {"title": "Pending approvals", "items": items}
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _confirm_card(self, title, rows, notes, action_id) -> dict:

        return {
            "title": title,
            "items": [
                {
                    "heading": title,
                    "rows": rows,
                    "notes": notes,
                    "buttons": [
                        _button("Confirm", f"/actions/{action_id}/confirm", {}, primary=True),
                        _button("Discard", f"/actions/{action_id}/discard", {}),
                    ]
                }
            ]
        }

    def _save_draft(self, session_id, draft: _Pending):

        if session_id:
            with self._lock:
                self._drafts[session_id] = draft

    def _take_draft(self, session_id) -> _Pending | None:

        if not session_id:
            return None

        with self._lock:
            draft = self._drafts.pop(session_id, None)

        return None if draft is None or draft.expired() else draft

    def _save_action(self, action: _Pending) -> str:

        action_id = uuid.uuid4().hex

        with self._lock:
            self._actions = {
                key: value for key, value in self._actions.items() if not value.expired()
            }
            self._actions[action_id] = action

        return action_id

    def _take_action(self, action_id: str, user_id: str) -> _Pending:

        with self._lock:
            action = self._actions.get(action_id)

            if action is None or action.expired() or action.user_id != user_id:
                raise HRSystemError(
                    "This request has expired or was already handled. Please ask again."
                )

            del self._actions[action_id]

        return action


@lru_cache(maxsize=1)
def get_task_service() -> TaskService:
    return TaskService()
