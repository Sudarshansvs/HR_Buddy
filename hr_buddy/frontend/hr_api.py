import os

import requests
import streamlit as st

# Where the FastAPI backend runs; shared by every page
API_URL = os.getenv("HR_BUDDY_API_URL", "http://localhost:8000")


def current_user() -> dict:
    return st.session_state["user"]


def sign_out():
    """Forget the login and everything tied to it (chat history, session id)."""
    st.session_state.clear()


def api(method: str, path: str, *, rerun_on_expiry: bool = True, timeout: int = 30, **kwargs) -> requests.Response:
    """Call the backend as the logged-in user.

    A 401 means the session expired or was revoked (e.g. a password reset), so the
    user is signed out. Pass rerun_on_expiry=False inside widget callbacks, where
    Streamlit reruns on its own afterwards.
    """
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    response = requests.request(
        method, f"{API_URL}{path}", headers=headers, timeout=timeout, **kwargs
    )

    if response.status_code == 401 and token:
        sign_out()
        if rerun_on_expiry:
            st.rerun()

    return response


def error_message(response: requests.Response) -> str:
    try:
        return response.json().get("detail") or response.text
    except ValueError:
        return response.text
