import requests
import streamlit as st

from hr_api import API_URL, error_message


# Centre a narrow column
outer = st.container(horizontal_alignment="center")
with outer.container(width=420):
    st.markdown("# 🤖 HR Buddy")
    st.caption("Sign in with your employee ID to continue.")

    with st.form("login", border=True):
        employee_id = st.text_input("Employee ID", placeholder="e.g. EMP1001")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")

    if submitted:
        if not employee_id.strip() or not password:
            st.error("Enter your employee ID and password.", icon=":material/error:")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/api/v1/auth/login",
                    json={"employee_id": employee_id.strip(), "password": password},
                    timeout=30,
                )
            except requests.RequestException:
                st.error(
                    "Can't reach the HR Buddy API. Please ensure it's running on localhost:8000.",
                    icon=":material/cloud_off:",
                )
            else:
                if response.ok:
                    data = response.json()
                    st.session_state.token = data["token"]
                    st.session_state.user = data["user"]
                    st.rerun()
                else:
                    st.error(error_message(response), icon=":material/error:")

    with st.expander("Demo accounts"):
        st.table(
            {
                "Employee ID": ["EMP1001", "MGR001", "HRADMIN","EMP1002"],
                "Password": ["Employee@123", "Manager@123", "Admin@123","Employee@123"],
                "Can access": ["Chat", "Chat, Approvals", "Chat, Admin"],
            }
        )
        st.caption("Employees who existed before logins were added use `Welcome@123`.")
