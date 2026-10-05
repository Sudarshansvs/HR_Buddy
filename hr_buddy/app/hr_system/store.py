"""A local mock HR system backed by SQLite.

Everything HR Buddy does to employee data goes through HRSystem, so it can be
swapped for a client of a real HRIS later without touching the chat code.
"""

import hashlib
import hmac
import secrets
import sqlite3
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from hr_buddy.app.core.config import settings


# Yearly entitlements. Annual matches leave_policy.txt; the rest are mock values.
LEAVE_ENTITLEMENTS = {
    "annual": 18,
    "casual": 6,
    "sick": 6,
}

TICKET_CATEGORIES = ["payroll", "documents", "it_access", "benefits", "other"]

TICKET_STATUSES = ["open", "in_progress", "resolved"]

ROLES = ["employee", "admin"]

# Demo accounts: (id, name, manager_id, role, password). Managers are simply
# employees with direct reports; "admin" is the HR admin role.
SEED_EMPLOYEES = [
    ("HRADMIN", "Meera Iyer", None, "admin", "Admin@123"),
    ("MGR001", "Priya Sharma", None, "employee", "Manager@123"),
    ("EMP1001", "Rahul Verma", "MGR001", "employee", "Employee@123"),
    ("EMP1002", "Anita Rao", "MGR001", "employee", "Employee@123"),
]

# Employees that existed before logins were added get this password; an HR admin can reset it
DEFAULT_PASSWORD = "Welcome@123"

MIN_PASSWORD_LENGTH = 8

SESSION_HOURS = 8

# leave_policy.txt: requests should be submitted two working days ahead
MIN_NOTICE_WORKING_DAYS = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    name TEXT,
    manager_id TEXT,
    role TEXT NOT NULL DEFAULT 'employee',
    password_hash TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    leave_type TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    days INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class HRSystemError(Exception):
    """A request the HR system refuses, with a message fit to show the employee."""


def working_days(start: date, end: date) -> int:
    """Count Monday-Friday days from start to end, inclusive."""

    return sum(
        1
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).weekday() < 5
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:

    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)

    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:

    if not stored:
        return False

    _, salt, expected = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)

    return hmac.compare_digest(digest.hex(), expected)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class HRSystem:

    def __init__(self, path: str = None, today: date = None):

        self.path = Path(path or settings.HR_DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        self._lock = threading.Lock()

        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)
            self._migrate()
            if not self._conn.execute("SELECT 1 FROM employees LIMIT 1").fetchone():
                self._seed(today or date.today())
            self._ensure_accounts()

    def _migrate(self):
        """Add login columns to databases created before logins existed."""

        columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(employees)")}

        if "role" not in columns:
            self._conn.execute("ALTER TABLE employees ADD COLUMN role TEXT NOT NULL DEFAULT 'employee'")

        if "password_hash" not in columns:
            self._conn.execute("ALTER TABLE employees ADD COLUMN password_hash TEXT")

    def _ensure_accounts(self):
        """Make sure the demo accounts exist and every employee can log in."""

        for employee_id, name, manager_id, role, password in SEED_EMPLOYEES:
            self._conn.execute(
                "INSERT OR IGNORE INTO employees (id, name, manager_id, role) VALUES (?, ?, ?, ?)",
                (employee_id, name, manager_id, role)
            )
            self._conn.execute(
                "UPDATE employees SET password_hash = ? WHERE id = ? AND password_hash IS NULL",
                (hash_password(password), employee_id)
            )

        for row in self._conn.execute("SELECT id FROM employees WHERE password_hash IS NULL").fetchall():
            self._conn.execute(
                "UPDATE employees SET password_hash = ? WHERE id = ?",
                (hash_password(DEFAULT_PASSWORD), row["id"])
            )

    def _seed(self, today: date):
        """Demo data: a manager with two reports who each have a request awaiting approval."""

        # Accounts and passwords are added by _ensure_accounts
        self._conn.executemany(
            "INSERT INTO employees (id, name, manager_id, role) VALUES (?, ?, ?, ?)",
            [(employee_id, name, manager_id, role) for employee_id, name, manager_id, role, _ in SEED_EMPLOYEES]
        )

        for employee_id, leave_type, offset, length in [
            ("EMP1001", "annual", 10, 3),
            ("EMP1002", "casual", 4, 1),
        ]:
            start = today + timedelta(days=offset)
            while start.weekday() >= 5:
                start += timedelta(days=1)
            end = start
            while working_days(start, end) < length:
                end += timedelta(days=1)
            self._conn.execute(
                """INSERT INTO leave_requests
                   (employee_id, leave_type, start_date, end_date, days, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                (employee_id, leave_type, start.isoformat(), end.isoformat(),
                 working_days(start, end), _now())
            )

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------

    def get_employee(self, employee_id: str) -> dict | None:
        """Public profile: id, name, manager_id, role and is_manager. Never the password hash."""

        with self._lock:
            row = self._conn.execute(
                """SELECT e.id, e.name, e.manager_id, e.role,
                          EXISTS(SELECT 1 FROM employees r WHERE r.manager_id = e.id) AS is_manager
                   FROM employees e WHERE e.id = ?""",
                (employee_id,)
            ).fetchone()

        if not row:
            return None

        return dict(row) | {"is_manager": bool(row["is_manager"])}

    def list_employees(self) -> list[dict]:

        with self._lock:
            ids = [row["id"] for row in self._conn.execute("SELECT id FROM employees ORDER BY id")]

        return [self.get_employee(employee_id) for employee_id in ids]

    def create_employee(self, employee_id: str, name: str, manager_id: str | None, role: str, password: str) -> dict:

        employee_id = employee_id.strip()

        if not employee_id:
            raise HRSystemError("Employee ID is required.")

        if role not in ROLES:
            raise HRSystemError(f"Role must be one of {', '.join(ROLES)}.")

        if manager_id and not self.get_employee(manager_id):
            raise HRSystemError(f"Manager {manager_id} doesn't exist.")

        self._check_password(password)

        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO employees (id, name, manager_id, role, password_hash) VALUES (?, ?, ?, ?, ?)",
                    (employee_id, name.strip() or None, manager_id or None, role, hash_password(password))
                )
            except sqlite3.IntegrityError:
                raise HRSystemError(f"Employee {employee_id} already exists.")

        return self.get_employee(employee_id)

    def set_password(self, employee_id: str, password: str):

        self._check_password(password)

        with self._lock, self._conn:
            updated = self._conn.execute(
                "UPDATE employees SET password_hash = ? WHERE id = ?",
                (hash_password(password), employee_id)
            ).rowcount

            # A reset signs the employee out everywhere
            self._conn.execute("DELETE FROM sessions WHERE employee_id = ?", (employee_id,))

        if not updated:
            raise HRSystemError(f"Employee {employee_id} doesn't exist.")

    def _check_password(self, password: str):

        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise HRSystemError(f"Passwords need at least {MIN_PASSWORD_LENGTH} characters.")

    # ------------------------------------------------------------------
    # Login sessions
    # ------------------------------------------------------------------

    def login(self, employee_id: str, password: str) -> str | None:
        """Return a new session token, or None if the ID or password is wrong."""

        with self._lock:
            row = self._conn.execute(
                "SELECT password_hash FROM employees WHERE id = ?", (employee_id,)
            ).fetchone()

        if not verify_password(password, row["password_hash"] if row else None):
            return None

        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)

        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?", (_now(),)
            )
            self._conn.execute(
                "INSERT INTO sessions (token_hash, employee_id, expires_at) VALUES (?, ?, ?)",
                (_hash_token(token), employee_id, expires.isoformat())
            )

        return token

    def user_for_token(self, token: str) -> dict | None:

        with self._lock:
            row = self._conn.execute(
                "SELECT employee_id FROM sessions WHERE token_hash = ? AND expires_at > ?",
                (_hash_token(token), _now())
            ).fetchone()

        return self.get_employee(row["employee_id"]) if row else None

    def logout(self, token: str):

        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),)
            )

    # ------------------------------------------------------------------
    # Leave
    # ------------------------------------------------------------------

    def leave_balance(self, employee_id: str, year: int = None) -> dict:
        """Per leave type: entitled, used (approved), pending and available days."""

        year = year or date.today().year

        with self._lock:
            rows = self._conn.execute(
                """SELECT leave_type, status, SUM(days) AS days FROM leave_requests
                   WHERE employee_id = ? AND status IN ('approved', 'pending')
                   AND substr(start_date, 1, 4) = ?
                   GROUP BY leave_type, status""",
                (employee_id, str(year))
            ).fetchall()

        balance = {
            leave_type: {"entitled": entitled, "used": 0, "pending": 0}
            for leave_type, entitled in LEAVE_ENTITLEMENTS.items()
        }

        for row in rows:
            key = "used" if row["status"] == "approved" else "pending"
            balance[row["leave_type"]][key] = row["days"]

        for values in balance.values():
            values["available"] = values["entitled"] - values["used"] - values["pending"]

        return balance

    def check_leave(self, employee_id: str, leave_type: str, start: date, end: date, today: date = None) -> dict:
        """Validate a leave request without creating it.

        Returns {"days": int, "warnings": [str]} or raises HRSystemError.
        """

        today = today or date.today()

        if leave_type not in LEAVE_ENTITLEMENTS:
            raise HRSystemError(f"Unknown leave type '{leave_type}'.")

        if end < start:
            raise HRSystemError("The end date is before the start date.")

        if start < today and leave_type != "sick":
            raise HRSystemError("Only sick leave can be applied for past dates.")

        if (today - start).days > 30:
            raise HRSystemError("Leave can't be applied more than 30 days in the past.")

        if start.year != end.year:
            raise HRSystemError("Please split leave that crosses into the next year into two requests.")

        days = working_days(start, end)

        if days == 0:
            raise HRSystemError("Those dates fall on a weekend, so no leave is needed.")

        with self._lock:
            overlap = self._conn.execute(
                """SELECT id FROM leave_requests
                   WHERE employee_id = ? AND status IN ('pending', 'approved')
                   AND start_date <= ? AND end_date >= ?""",
                (employee_id, end.isoformat(), start.isoformat())
            ).fetchone()

        if overlap:
            raise HRSystemError(
                f"You already have leave request LR-{overlap['id']} covering some of these dates."
            )

        available = self.leave_balance(employee_id, start.year)[leave_type]["available"]

        if days > available:
            raise HRSystemError(
                f"This needs {days} day(s) of {leave_type} leave, but you only have {available} available."
            )

        warnings = []

        if leave_type != "sick" and working_days(today + timedelta(days=1), start - timedelta(days=1)) < MIN_NOTICE_WORKING_DAYS:
            warnings.append(
                "The leave policy asks for requests at least two working days in advance; "
                "your manager may still approve it."
            )

        return {"days": days, "warnings": warnings}

    def create_leave_request(self, employee_id: str, leave_type: str, start: date, end: date, today: date = None) -> dict:

        days = self.check_leave(employee_id, leave_type, start, end, today)["days"]

        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO leave_requests
                   (employee_id, leave_type, start_date, end_date, days, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                (employee_id, leave_type, start.isoformat(), end.isoformat(), days, _now())
            )

        return self.get_leave_request(cursor.lastrowid)

    def get_leave_request(self, request_id: int) -> dict | None:

        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM leave_requests WHERE id = ?", (request_id,)
            ).fetchone()

        return dict(row) if row else None

    def list_leave_requests(self, employee_id: str) -> list[dict]:

        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM leave_requests WHERE employee_id = ? ORDER BY start_date DESC",
                (employee_id,)
            ).fetchall()

        return [dict(row) for row in rows]

    def cancellable_requests(self, employee_id: str, today: date = None) -> list[dict]:

        today = today or date.today()

        return [
            request
            for request in self.list_leave_requests(employee_id)
            if request["status"] in ("pending", "approved")
            and date.fromisoformat(request["start_date"]) > today
        ]

    def cancel_leave_request(self, employee_id: str, request_id: int, today: date = None) -> dict:

        request = self.get_leave_request(request_id)

        if not request or request["employee_id"] != employee_id:
            raise HRSystemError(f"LR-{request_id} is not one of your leave requests.")

        if request not in self.cancellable_requests(employee_id, today):
            raise HRSystemError(
                f"LR-{request_id} can't be cancelled because it is {request['status']} "
                "or has already started."
            )

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE leave_requests SET status = 'cancelled', decided_at = ? WHERE id = ?",
                (_now(), request_id)
            )

        return self.get_leave_request(request_id)

    def pending_approvals(self, manager_id: str) -> list[dict]:

        with self._lock:
            rows = self._conn.execute(
                """SELECT r.*, e.name AS employee_name FROM leave_requests r
                   JOIN employees e ON e.id = r.employee_id
                   WHERE e.manager_id = ? AND r.status = 'pending'
                   ORDER BY r.start_date""",
                (manager_id,)
            ).fetchall()

        return [dict(row) for row in rows]

    def team_requests(self, manager_id: str) -> list[dict]:
        """Every leave request from the manager's direct reports, newest first."""

        with self._lock:
            rows = self._conn.execute(
                """SELECT r.*, e.name AS employee_name FROM leave_requests r
                   JOIN employees e ON e.id = r.employee_id
                   WHERE e.manager_id = ?
                   ORDER BY r.created_at DESC""",
                (manager_id,)
            ).fetchall()

        return [dict(row) for row in rows]

    def team_size(self, manager_id: str) -> int:

        with self._lock:
            return self._conn.execute(
                "SELECT COUNT(*) FROM employees WHERE manager_id = ?", (manager_id,)
            ).fetchone()[0]

    def decide_leave_request(self, manager_id: str, request_id: int, approve: bool) -> dict:

        if request_id not in {request["id"] for request in self.pending_approvals(manager_id)}:
            raise HRSystemError(
                f"LR-{request_id} is not a pending request from someone who reports to you."
            )

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE leave_requests SET status = ?, decided_by = ?, decided_at = ? WHERE id = ?",
                ("approved" if approve else "rejected", manager_id, _now(), request_id)
            )

        return self.get_leave_request(request_id)

    # ------------------------------------------------------------------
    # Tickets
    # ------------------------------------------------------------------

    def create_ticket(self, employee_id: str, category: str, description: str) -> dict:

        if category not in TICKET_CATEGORIES:
            raise HRSystemError(f"Unknown ticket category '{category}'.")

        if not description.strip():
            raise HRSystemError("Please describe the issue.")

        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO tickets (employee_id, category, description, status, created_at)
                   VALUES (?, ?, ?, 'open', ?)""",
                (employee_id, category, description.strip(), _now())
            )
            row = self._conn.execute(
                "SELECT * FROM tickets WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()

        return dict(row)

    def all_tickets(self) -> list[dict]:

        with self._lock:
            rows = self._conn.execute(
                """SELECT t.*, e.name AS employee_name FROM tickets t
                   LEFT JOIN employees e ON e.id = t.employee_id
                   ORDER BY t.id DESC"""
            ).fetchall()

        return [dict(row) for row in rows]

    def set_ticket_status(self, ticket_id: int, status: str) -> dict:

        if status not in TICKET_STATUSES:
            raise HRSystemError(f"Status must be one of {', '.join(TICKET_STATUSES)}.")

        with self._lock, self._conn:
            updated = self._conn.execute(
                "UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id)
            ).rowcount

        if not updated:
            raise HRSystemError(f"Ticket TKT-{ticket_id} doesn't exist.")

        return {"id": ticket_id, "status": status}

    def all_leave_requests(self) -> list[dict]:

        with self._lock:
            rows = self._conn.execute(
                """SELECT r.*, e.name AS employee_name FROM leave_requests r
                   LEFT JOIN employees e ON e.id = r.employee_id
                   ORDER BY r.start_date DESC"""
            ).fetchall()

        return [dict(row) for row in rows]

    def list_tickets(self, employee_id: str) -> list[dict]:

        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tickets WHERE employee_id = ? ORDER BY id DESC",
                (employee_id,)
            ).fetchall()

        return [dict(row) for row in rows]
