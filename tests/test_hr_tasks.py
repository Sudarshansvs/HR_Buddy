import pathlib
import sys
from datetime import date

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hr_buddy.app.hr_system.store import HRSystem, HRSystemError, working_days
from hr_buddy.app.tasks.parsing import (
    is_cancel,
    leave_type_from,
    simple_dates_from,
    ticket_category_from
)


MONDAY = date(2026, 10, 5)


@pytest.fixture
def hr(tmp_path):
    hr = HRSystem(path=str(tmp_path / "hr.sqlite3"), today=MONDAY)
    hr.create_employee("EMP9", "Test Person", "MGR001", "employee", "Password@1")
    return hr


def test_working_days_skip_weekends():
    assert working_days(date(2026, 10, 9), date(2026, 10, 12)) == 2  # Fri -> Mon


def test_new_employee_gets_full_balance(hr):
    assert hr.leave_balance("EMP9", 2026)["annual"]["available"] == 18


def test_login_and_sessions(hr):
    assert hr.login("EMP9", "wrong-password") is None
    assert hr.login("NOBODY", "Password@1") is None

    token = hr.login("EMP9", "Password@1")
    assert hr.user_for_token(token)["id"] == "EMP9"
    assert hr.user_for_token("made-up-token") is None

    hr.logout(token)
    assert hr.user_for_token(token) is None


def test_password_reset_revokes_sessions(hr):
    token = hr.login("EMP9", "Password@1")
    hr.set_password("EMP9", "Changed@123")

    assert hr.user_for_token(token) is None
    assert hr.login("EMP9", "Password@1") is None
    assert hr.login("EMP9", "Changed@123")

    with pytest.raises(HRSystemError, match="at least 8"):
        hr.set_password("EMP9", "short")


def test_roles(hr):
    assert hr.get_employee("MGR001")["is_manager"]
    assert not hr.get_employee("EMP9")["is_manager"]
    assert hr.get_employee("HRADMIN")["role"] == "admin"
    assert "password_hash" not in hr.get_employee("EMP9")

    with pytest.raises(HRSystemError, match="already exists"):
        hr.create_employee("EMP9", "Again", None, "employee", "Password@1")


def test_existing_employees_get_default_password(tmp_path):
    import sqlite3
    path = tmp_path / "old.sqlite3"
    # A database from before logins existed
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE employees (id TEXT PRIMARY KEY, name TEXT, manager_id TEXT)")
        conn.execute("INSERT INTO employees VALUES ('123456', NULL, 'MGR001')")

    hr = HRSystem(path=str(path), today=MONDAY)

    assert hr.login("123456", "Welcome@123")
    assert hr.login("MGR001", "Manager@123")


def test_leave_request_reserves_balance(hr):
    hr.create_leave_request("EMP9", "casual", date(2026, 10, 12), date(2026, 10, 14), MONDAY)
    balance = hr.leave_balance("EMP9", 2026)["casual"]
    assert (balance["pending"], balance["available"]) == (3, 3)


@pytest.mark.parametrize("leave_type, start, end, message", [
    ("casual", date(2026, 10, 14), date(2026, 10, 12), "before the start"),
    ("casual", date(2026, 10, 1), date(2026, 10, 1), "Only sick leave"),
    ("casual", date(2026, 10, 10), date(2026, 10, 11), "weekend"),
    ("casual", date(2026, 10, 12), date(2026, 10, 30), "only have 6"),
])
def test_invalid_leave_is_refused(hr, leave_type, start, end, message):
    with pytest.raises(HRSystemError, match=message):
        hr.check_leave("EMP9", leave_type, start, end, MONDAY)


def test_overlapping_leave_is_refused(hr):
    hr.create_leave_request("EMP9", "annual", date(2026, 10, 12), date(2026, 10, 14), MONDAY)
    with pytest.raises(HRSystemError, match="already have"):
        hr.check_leave("EMP9", "casual", date(2026, 10, 14), date(2026, 10, 15), MONDAY)


def test_short_notice_warns_but_allows(hr):
    check = hr.check_leave("EMP9", "casual", date(2026, 10, 6), date(2026, 10, 6), MONDAY)
    assert check["days"] == 1 and check["warnings"]


def test_only_the_manager_can_decide(hr):
    request = hr.create_leave_request("EMP9", "annual", date(2026, 10, 19), date(2026, 10, 19), MONDAY)

    with pytest.raises(HRSystemError):
        hr.decide_leave_request("EMP1001", request["id"], approve=True)

    assert hr.decide_leave_request("MGR001", request["id"], approve=True)["status"] == "approved"
    assert hr.leave_balance("EMP9", 2026)["annual"]["used"] == 1

    with pytest.raises(HRSystemError):
        hr.decide_leave_request("MGR001", request["id"], approve=False)


def test_only_the_owner_can_cancel(hr):
    request = hr.create_leave_request("EMP9", "annual", date(2026, 10, 19), date(2026, 10, 19), MONDAY)

    with pytest.raises(HRSystemError):
        hr.cancel_leave_request("EMP1001", request["id"], MONDAY)

    assert hr.cancel_leave_request("EMP9", request["id"], MONDAY)["status"] == "cancelled"
    assert hr.leave_balance("EMP9", 2026)["annual"]["available"] == 18


def test_seeded_manager_has_pending_approvals(hr):
    assert {r["employee_id"] for r in hr.pending_approvals("MGR001")} == {"EMP1001", "EMP1002"}


@pytest.mark.parametrize("text, expected", [
    ("apply casual leave for tomorrow", (date(2026, 10, 6), date(2026, 10, 6))),
    ("sick leave today, I have fever", (MONDAY, MONDAY)),
    ("next Monday to Wednesday", (date(2026, 10, 12), date(2026, 10, 14))),
    ("take Wednesday and Thursday off", (date(2026, 10, 7), date(2026, 10, 8))),
    ("I need 3 days off", None),
])
def test_simple_dates(text, expected):
    assert simple_dates_from(text, MONDAY) == expected


def test_keyword_parsing():
    assert leave_type_from("I have fever") == "sick"
    assert leave_type_from("I need some days off") is None
    assert ticket_category_from("my salary hasn't been credited") == "payroll"
    assert ticket_category_from("my manager is rude") == "other"
    assert is_cancel("never mind") and not is_cancel("from 12th to 14th")
