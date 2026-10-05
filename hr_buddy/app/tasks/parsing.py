"""Deterministic parsing for task details.

A 3B model guesses when a detail is missing and stumbles on simple relative dates,
so anything that keywords can settle is settled here; the LLM only handles
explicit dates such as "12th to 14th October".
"""

import re
from datetime import date, timedelta


LEAVE_TYPE_KEYWORDS = {
    "sick": ["sick", "fever", "ill", "unwell", "doctor", "hospital", "medical", "cold", "flu"],
    "casual": ["casual"],
    "annual": ["annual", "vacation", "holiday", "earned", "privilege"],
}

TICKET_CATEGORY_KEYWORDS = {
    "payroll": ["salary", "pay", "payslip", "payroll", "reimbursement", "bonus", "tax", "credited"],
    "it_access": ["laptop", "access", "login", "password", "vpn", "email", "account", "portal", "system"],
    "documents": ["document", "letter", "certificate", "id card", "badge", "offer"],
    "benefits": ["insurance", "benefit", "medical cover", "health", "pf", "provident"],
}

CANCEL_WORDS = ["cancel", "never mind", "nevermind", "forget it", "stop", "don't apply", "dont apply"]

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

RELATIVE_DAYS = {
    "day after tomorrow": 2,
    "tomorrow": 1,
    "today": 0,
    "yesterday": -1,
}


def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9 ]", " ", text.lower()) + " "


def _has_word(text: str, word: str) -> bool:
    return f" {word} " in _words(text)


def leave_type_from(text: str) -> str | None:

    for leave_type, keywords in LEAVE_TYPE_KEYWORDS.items():
        if any(_has_word(text, keyword) for keyword in keywords):
            return leave_type

    return None


def ticket_category_from(text: str) -> str:

    for category, keywords in TICKET_CATEGORY_KEYWORDS.items():
        if any(_has_word(text, keyword) for keyword in keywords):
            return category

    return "other"


def is_cancel(text: str) -> bool:

    return any(_has_word(text, word) for word in CANCEL_WORDS)


def has_explicit_date(text: str) -> bool:
    """Digits in the message mean dates like "14th" or "14/10" that need the LLM."""

    return bool(re.search(r"\d", text))


def simple_dates_from(text: str, today: date) -> tuple[date, date] | None:
    """Resolve "today", "tomorrow" and weekday names; None if there are none.

    Each weekday resolves to its first occurrence after the previous date found,
    so "next Monday to Wednesday" is a Monday followed by the Wednesday after it.
    """

    words = _words(text)

    found = []

    for phrase, offset in RELATIVE_DAYS.items():
        if f" {phrase} " in words:
            found.append(today + timedelta(days=offset))
            words = words.replace(f" {phrase} ", " ")

    anchor = max(found) if found else today

    for match in re.finditer(r"\b(next )?(" + "|".join(WEEKDAYS) + r")\b", words):
        weekday = WEEKDAYS.index(match.group(2))
        days_ahead = (weekday - anchor.weekday()) % 7 or 7
        anchor = anchor + timedelta(days=days_ahead)
        found.append(anchor)

    if not found:
        return None

    return min(found), max(found)
