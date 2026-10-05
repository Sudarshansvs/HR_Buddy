import calendar
from datetime import date

import requests
import streamlit as st

from hr_api import api, error_message

STATUS_COLORS = {"approved": "green", "pending": "orange"}

TYPE_ICONS = {
    "annual": ":material/beach_access:",
    "casual": ":material/event_available:",
    "sick": ":material/sick:",
}


def first_of_month(day: date) -> date:
    return day.replace(day=1)


def shift_month(months: int):
    """Button callback: move the calendar forward or back by whole months."""
    current = st.session_state.calendar_month
    index = current.year * 12 + current.month - 1 + months
    st.session_state.calendar_month = date(index // 12, index % 12 + 1, 1)


def go_to_today():
    st.session_state.calendar_month = first_of_month(date.today())


def is_off(leave: dict, day: date) -> bool:
    # Leave only counts on working days, so weekends inside a request stay clear
    return day.weekday() < 5 and leave["start_date"] <= day.isoformat() <= leave["end_date"]


today = date.today()

if "calendar_month" not in st.session_state:
    go_to_today()

month = st.session_state.calendar_month
weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)
month_days = [day for week in weeks for day in week if day.month == month.month]

st.markdown("## Team calendar")

# --------------------------------------------------------
# MONTH NAVIGATION
# --------------------------------------------------------

with st.container(horizontal=True, vertical_alignment="center"):
    st.button("", icon=":material/chevron_left:", key="prev_month", help="Previous month",
              on_click=shift_month, args=(-1,))
    st.markdown(f"### {month:%B %Y}")
    st.button("", icon=":material/chevron_right:", key="next_month", help="Next month",
              on_click=shift_month, args=(1,))
    st.button("Today", icon=":material/today:", type="tertiary", on_click=go_to_today)
    st.space("stretch")
    statuses = st.pills(
        "Show",
        ["Approved", "Pending"],
        default=["Approved", "Pending"],
        selection_mode="multi",
        key="calendar_statuses",
        label_visibility="collapsed",
    )
    st.button("Refresh", icon=":material/refresh:", type="tertiary")

# --------------------------------------------------------
# LOAD LEAVE FOR THE VISIBLE WEEKS
# --------------------------------------------------------

try:
    response = api(
        "GET",
        "/api/v1/tasks/team/calendar",
        params={"start": weeks[0][0].isoformat(), "end": weeks[-1][-1].isoformat()},
        timeout=15,
    )
except requests.RequestException as error:
    st.error(f"Could not load the team calendar: {error}", icon=":material/error:")
    st.info("Please ensure the HR Buddy API is running on localhost:8000")
    st.stop()

if not response.ok:
    st.error(error_message(response), icon=":material/block:")
    st.stop()

data = response.json()
wanted = {status.lower() for status in statuses}
leaves = [leave for leave in data["leaves"] if leave["status"] in wanted]

# --------------------------------------------------------
# SUMMARY
# --------------------------------------------------------

off_today = [leave for leave in leaves if leave["status"] == "approved" and is_off(leave, today)]

with st.container(horizontal=True):
    st.metric("Team size", data["team_size"], border=True)
    st.metric(
        "Off today",
        len(off_today),
        border=True,
        help=", ".join(l["employee_name"] or l["employee_id"] for l in off_today) or "Everyone is in today.",
    )
    st.metric(
        f"Leave days in {month:%B}",
        sum(is_off(leave, day) for leave in leaves for day in month_days),
        border=True,
        help="Working days of leave that fall in this month, for the statuses shown.",
    )
    st.metric(
        "Awaiting approval",
        sum(leave["status"] == "pending" for leave in leaves),
        border=True,
        help="Pending requests touching this month. Decide on them from the Approvals page.",
    )

# --------------------------------------------------------
# MONTH GRID
# --------------------------------------------------------

st.caption(
    ":green-badge[Approved] :orange-badge[Pending] · "
    ":material/beach_access: Annual · :material/event_available: Casual · :material/sick: Sick"
)

header = st.columns(7, gap="small")
for column, name in zip(header, calendar.day_abbr):
    column.markdown(f"**{name}**")

for week in weeks:
    for column, day in zip(st.columns(7, gap="small"), week):
        with column.container(border=True, height=150, gap="xsmall"):
            if day.month != month.month:
                st.markdown(f":gray[{day.day}]")
                continue

            if day == today:
                st.badge(str(day.day), color="primary", icon=":material/today:")
            elif day.weekday() >= 5:
                st.markdown(f":gray[{day.day}]")
            else:
                st.markdown(f"**{day.day}**")

            for leave in leaves:
                if is_off(leave, day):
                    name = (leave["employee_name"] or leave["employee_id"]).split()[0]
                    st.badge(
                        name,
                        icon=TYPE_ICONS.get(leave["leave_type"]),
                        color=STATUS_COLORS[leave["status"]],
                        help=f"{leave['employee_name'] or leave['employee_id']} · "
                             f"{leave['leave_type'].capitalize()} leave · {leave['status']} · LR-{leave['id']}",
                    )

# --------------------------------------------------------
# LEAVE LIST
# --------------------------------------------------------

in_month = [
    leave for leave in leaves
    if leave["start_date"] <= month_days[-1].isoformat() and leave["end_date"] >= month_days[0].isoformat()
]

st.markdown(f"#### Leave in {month:%B %Y}")

if not in_month:
    st.info("No one on the team has leave this month.", icon=":material/event_available:")
else:
    st.dataframe(
        [
            {
                "Request": f"LR-{leave['id']}",
                "Employee": leave["employee_name"] or leave["employee_id"],
                "Type": leave["leave_type"].capitalize(),
                "From": date.fromisoformat(leave["start_date"]),
                "To": date.fromisoformat(leave["end_date"]),
                "Days": leave["days"],
                "Status": leave["status"].capitalize(),
            }
            for leave in in_month
        ],
        hide_index=True,
        column_config={
            "From": st.column_config.DateColumn(format="ddd D MMM"),
            "To": st.column_config.DateColumn(format="ddd D MMM"),
        },
    )
