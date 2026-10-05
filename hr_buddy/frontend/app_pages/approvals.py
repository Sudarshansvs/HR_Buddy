from datetime import date, datetime

import requests
import streamlit as st

from hr_api import api, error_message


def format_dates(start: str, end: str) -> str:
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start == end:
        return f"{start:%a %d %b %Y}"
    return f"{start:%a %d %b} → {end:%a %d %b %Y}"


def decide(request_id: int, approve: bool, label: str):
    """Button callback: record the decision, then show the outcome after the rerun."""
    try:
        response = api(
            "POST",
            f"/api/v1/tasks/leave-requests/{request_id}/decision",
            json={"approve": approve},
            rerun_on_expiry=False,
        )
        message = response.json().get("message") if response.ok else error_message(response)
        st.session_state.approvals_flash = (response.ok, message or f"{label} LR-{request_id}.")
    except (requests.RequestException, ValueError) as error:
        st.session_state.approvals_flash = (False, f"Could not reach HR Buddy: {error}")


st.markdown("## Leave approvals")

try:
    response = api("GET", "/api/v1/tasks/team", timeout=15)
except requests.RequestException as error:
    st.error(f"Could not load approvals: {error}", icon=":material/error:")
    st.info("Please ensure the HR Buddy API is running on localhost:8000")
    st.stop()

if not response.ok:
    # e.g. 403 if their last report moved to another manager since they signed in
    st.error(error_message(response), icon=":material/block:")
    st.stop()

team = response.json()

flash = st.session_state.pop("approvals_flash", None)
if flash:
    ok, message = flash
    if ok:
        st.toast(message, icon=":material/check_circle:")
    else:
        st.error(message, icon=":material/error:")

pending = team["pending"]

with st.container(horizontal=True, vertical_alignment="center"):
    st.caption(f"{team['team_size']} direct report(s)")
    st.space("stretch")
    st.button("Refresh", icon=":material/refresh:", type="tertiary")

# --------------------------------------------------------
# SUMMARY
# --------------------------------------------------------

today = date.today()

with st.container(horizontal=True):
    st.metric("Pending requests", len(pending), border=True)
    st.metric("Days requested", sum(r["days"] for r in pending), border=True)
    st.metric(
        "Short notice",
        sum(r["short_notice"] for r in pending),
        border=True,
        help="Less than two working days' notice, which the leave policy asks for.",
    )
    st.metric(
        "Overlapping",
        sum(bool(r["overlaps"]) for r in pending),
        border=True,
        help="Someone else on the team is off or has asked to be off on some of the same dates.",
    )

# --------------------------------------------------------
# PENDING REQUESTS
# --------------------------------------------------------

st.markdown("#### Waiting for your decision")

if not pending:
    st.success("You're all caught up. No requests are waiting for you.", icon=":material/task_alt:")

view = st.segmented_control(
    "Show",
    ["All", "Short notice", "Overlapping"],
    default="All",
    required=True,
    key="approvals_view",
    label_visibility="collapsed",
) if pending else None

if view == "Short notice":
    pending = [r for r in pending if r["short_notice"]]
elif view == "Overlapping":
    pending = [r for r in pending if r["overlaps"]]

for request in pending:
    name = request["employee_name"] or request["employee_id"]
    leave_type = request["leave_type"].capitalize()

    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f"**{name}** · {leave_type} leave · `LR-{request['id']}`")
            st.space("stretch")
            if request["short_notice"]:
                st.badge("Short notice", icon=":material/schedule:", color="orange")
            if request["overlaps"]:
                st.badge("Overlaps with team", icon=":material/group:", color="violet")

        st.markdown(
            f"- **Dates:** {format_dates(request['start_date'], request['end_date'])} "
            f"({request['days']} working day(s))\n"
            f"- **Balance if approved:** {request['available_after']} of "
            f"{request['entitled']} {request['leave_type']} days left\n"
            f"- **Notice given:** {request['notice_working_days']} working day(s)\n"
            f"- **Requested:** {datetime.fromisoformat(request['created_at']):%d %b %Y, %H:%M} UTC"
        )

        for other in request["overlaps"]:
            st.caption(
                f":material/event_busy: {other['employee_name']} is also off "
                f"{format_dates(other['start_date'], other['end_date'])} ({other['status']})"
            )

        with st.container(horizontal=True):
            st.button(
                "Approve",
                key=f"approve_{request['id']}",
                type="primary",
                icon=":material/check:",
                on_click=decide,
                args=(request["id"], True, "Approved"),
            )
            st.button(
                "Reject",
                key=f"reject_{request['id']}",
                icon=":material/close:",
                on_click=decide,
                args=(request["id"], False, "Rejected"),
            )

# --------------------------------------------------------
# RECENT DECISIONS
# --------------------------------------------------------

decisions = team["recent_decisions"]

if decisions:
    st.markdown("#### Your recent decisions")
    st.dataframe(
        [
            {
                "Request": f"LR-{r['id']}",
                "Employee": r["employee_name"] or r["employee_id"],
                "Type": r["leave_type"].capitalize(),
                "Dates": format_dates(r["start_date"], r["end_date"]),
                "Days": r["days"],
                "Decision": r["status"].capitalize(),
                "Decided": datetime.fromisoformat(r["decided_at"]),
            }
            for r in decisions
        ],
        hide_index=True,
        column_config={
            "Decided": st.column_config.DatetimeColumn(format="D MMM YYYY, HH:mm"),
        },
    )
