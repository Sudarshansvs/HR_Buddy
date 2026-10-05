import streamlit as st

from hr_api import api, sign_out

st.set_page_config(
    page_title="HR Buddy",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

user = st.session_state.get("user")


def log_out():
    try:
        api("POST", "/api/v1/auth/logout", rerun_on_expiry=False, timeout=10)
    except Exception:
        pass
    sign_out()


if not user:
    page = st.navigation(
        [st.Page("app_pages/login.py", title="Sign in", icon=":material/login:")],
        position="hidden",
    )
    page.run()
    st.stop()

# Pages follow the role; the backend enforces the same rules on every request
pages = [st.Page("app_pages/chat.py", title="Chat", icon=":material/chat:", default=True)]

if user["is_manager"]:
    pages.append(st.Page("app_pages/approvals.py", title="Approvals", icon=":material/fact_check:"))
    pages.append(st.Page("app_pages/team_calendar.py", title="Team calendar", icon=":material/calendar_month:"))

if user["role"] == "admin":
    pages.append(st.Page("app_pages/admin.py", title="Admin", icon=":material/admin_panel_settings:"))

with st.sidebar:
    roles = ["HR admin" if user["role"] == "admin" else "Employee"]
    if user["is_manager"]:
        roles.append("Manager")

    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"**{user['name'] or user['id']}**  \n:gray[{user['id']} · {' & '.join(roles)}]")
        st.space("stretch")
        st.button("Log out", icon=":material/logout:", type="tertiary", on_click=log_out)

    st.divider()

page = st.navigation(pages, position="top")
page.run()
