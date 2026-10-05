from datetime import datetime

import requests
import streamlit as st

from hr_api import api, error_message


TICKET_STATUSES = ["open", "in_progress", "resolved"]


def load(path: str):
    try:
        response = api("GET", path, timeout=15)
    except requests.RequestException as error:
        st.error(f"Could not reach HR Buddy: {error}", icon=":material/cloud_off:")
        st.stop()
    if not response.ok:
        st.error(error_message(response), icon=":material/block:")
        st.stop()
    return response.json()


def show_result(response: requests.Response, success: str):
    if response.ok:
        st.toast(success, icon=":material/check_circle:")
    else:
        st.error(error_message(response), icon=":material/error:")


st.markdown("## HR admin")

tickets_tab, leave_tab, people_tab, docs_tab = st.tabs(
    [":material/confirmation_number: Tickets", ":material/event: Leave requests",
     ":material/group: People", ":material/library_books: Knowledge base"]
)

# --------------------------------------------------------
# TICKETS
# --------------------------------------------------------

with tickets_tab:
    tickets = load("/api/v1/admin/tickets")

    with st.container(horizontal=True):
        for status in TICKET_STATUSES:
            st.metric(
                status.replace("_", " ").capitalize(),
                sum(t["status"] == status for t in tickets),
                border=True,
            )

    if not tickets:
        st.info("No tickets have been raised yet.", icon=":material/inbox:")
    else:
        st.caption("Change a status, then save.")
        edited = st.data_editor(
            [
                {
                    "ID": t["id"],
                    "Employee": t["employee_name"] or t["employee_id"],
                    "Category": t["category"].replace("_", " ").capitalize(),
                    "Issue": t["description"],
                    "Raised": datetime.fromisoformat(t["created_at"]),
                    "Status": t["status"],
                }
                for t in tickets
            ],
            key="tickets_editor",
            hide_index=True,
            disabled=["ID", "Employee", "Category", "Issue", "Raised"],
            column_config={
                "ID": st.column_config.NumberColumn(format="TKT-%d", width="small"),
                "Issue": st.column_config.TextColumn(width="large"),
                "Raised": st.column_config.DatetimeColumn(format="D MMM YYYY, HH:mm"),
                "Status": st.column_config.SelectboxColumn(options=TICKET_STATUSES, required=True),
            },
        )

        original = {t["id"]: t["status"] for t in tickets}
        changes = [row for row in edited if row["Status"] != original[row["ID"]]]

        if st.button(
            f"Save {len(changes)} change(s)" if changes else "No changes",
            type="primary",
            disabled=not changes,
            icon=":material/save:",
        ):
            for row in changes:
                response = api("PATCH", f"/api/v1/admin/tickets/{row['ID']}", json={"status": row["Status"]})
                show_result(response, f"TKT-{row['ID']} is now {row['Status'].replace('_', ' ')}.")
            st.session_state.pop("tickets_editor", None)
            st.rerun()

# --------------------------------------------------------
# LEAVE REQUESTS
# --------------------------------------------------------

with leave_tab:
    leave_requests = load("/api/v1/admin/leave-requests")

    status_filter = st.segmented_control(
        "Status",
        ["pending", "approved", "rejected", "cancelled"],
        selection_mode="multi",
        default=["pending", "approved"],
        key="admin_leave_status",
    )

    st.dataframe(
        [
            {
                "ID": r["id"],
                "Employee": r["employee_name"] or r["employee_id"],
                "Type": r["leave_type"].capitalize(),
                "From": r["start_date"],
                "To": r["end_date"],
                "Days": r["days"],
                "Status": r["status"].capitalize(),
                "Decided by": r["decided_by"] or "",
            }
            for r in leave_requests
            if r["status"] in status_filter
        ],
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(format="LR-%d", width="small"),
            "From": st.column_config.DateColumn(format="ddd D MMM YYYY"),
            "To": st.column_config.DateColumn(format="ddd D MMM YYYY"),
        },
    )
    st.caption("Requests are approved by each employee's manager, on the Approvals page.")

# --------------------------------------------------------
# PEOPLE
# --------------------------------------------------------

with people_tab:
    employees = load("/api/v1/admin/employees")
    names = {e["id"]: e["name"] or e["id"] for e in employees}

    st.dataframe(
        [
            {
                "Employee ID": e["id"],
                "Name": e["name"] or "",
                "Manager": names.get(e["manager_id"], "") if e["manager_id"] else "",
                "Role": "HR admin" if e["role"] == "admin" else "Employee",
                "Manages a team": e["is_manager"],
            }
            for e in employees
        ],
        hide_index=True,
    )

    add_column, reset_column = st.columns(2)

    with add_column:
        with st.form("add_employee", clear_on_submit=True):
            st.markdown("**Add an employee**")
            new_id = st.text_input("Employee ID")
            new_name = st.text_input("Name")
            new_manager = st.selectbox(
                "Manager",
                [None] + list(names),
                format_func=lambda employee_id: "No manager" if employee_id is None else f"{names[employee_id]} ({employee_id})",
            )
            new_role = st.segmented_control(
                "Role", ["employee", "admin"], default="employee", required=True,
                format_func=lambda role: "HR admin" if role == "admin" else "Employee",
            )
            new_password = st.text_input("Temporary password", type="password", help="At least 8 characters.")
            if st.form_submit_button("Add employee", type="primary", icon=":material/person_add:"):
                response = api(
                    "POST",
                    "/api/v1/admin/employees",
                    json={
                        "employee_id": new_id,
                        "name": new_name,
                        "manager_id": new_manager,
                        "role": new_role,
                        "password": new_password,
                    },
                )
                show_result(response, f"Added {new_id}. Share the temporary password with them.")
                if response.ok:
                    st.rerun()

    with reset_column:
        with st.form("reset_password", clear_on_submit=True):
            st.markdown("**Reset a password**")
            reset_id = st.selectbox(
                "Employee", list(names),
                format_func=lambda employee_id: f"{names[employee_id]} ({employee_id})",
            )
            reset_password = st.text_input("New password", type="password", help="At least 8 characters.")
            st.caption("They'll be signed out everywhere.")
            if st.form_submit_button("Reset password", icon=":material/lock_reset:"):
                response = api(
                    "POST",
                    f"/api/v1/admin/employees/{reset_id}/password",
                    json={"password": reset_password},
                )
                show_result(response, f"Password reset for {reset_id}.")

# --------------------------------------------------------
# KNOWLEDGE BASE
# --------------------------------------------------------

with docs_tab:
    info = load("/api/v1/documents/info")

    documents = info.get("documents_by_name", {})
    if documents:
        st.dataframe(
            [{"Document": name, "Chunks": count} for name, count in documents.items()],
            hide_index=True,
        )

    uploaded_file = st.file_uploader(
        "Upload a policy document",
        type=["txt", "md", "pdf"],
        help="It's indexed straight away and HR Buddy can answer from it.",
    )

    # Avoid uploading the same file again on every rerun
    if uploaded_file is not None and st.session_state.get("last_uploaded_file") != uploaded_file.name:
        with st.spinner("Uploading and indexing..."):
            response = api(
                "POST",
                "/api/v1/documents/upload",
                files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                timeout=120,
            )
        if response.ok:
            data = response.json()
            st.session_state.last_uploaded_file = uploaded_file.name
            # Lets the chat page offer this file as a knowledge source
            st.session_state.uploaded_filename = data.get("filename", uploaded_file.name)
            st.success(data.get("message", "Uploaded"), icon=":material/check_circle:")
            if data.get("preview"):
                with st.expander("Preview"):
                    st.text(data["preview"][:500])
        else:
            st.error(error_message(response), icon=":material/error:")
