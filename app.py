import time

import streamlit as st
import requests


BACKEND_URL = "http://127.0.0.1:8080/ask"


st.set_page_config(
    page_title="HR Buddy",
    page_icon="🤖"
)

st.title("🤖 HR Buddy")

question = st.text_input(
    "Ask your HR question"
)


def ask_backend(question_text: str):
    last_error = None

    for _ in range(15):
        try:
            return requests.post(
                BACKEND_URL,
                json={"question": question_text},
                timeout=30,
            )
        except requests.exceptions.ConnectionError as exc:
            last_error = exc
            time.sleep(1)

    raise last_error


if st.button("Ask HR Buddy"):

    if not question:

        st.warning("Please enter a question.")

    else:
        try:
            response = ask_backend(question)
        except requests.exceptions.RequestException:
            st.error(
                "The HR Buddy backend is not running. Start it with `python run.py` "
                "or run `uvicorn llm_test_2:app --host 127.0.0.1 --port 8080`."
            )
            st.stop()

        if response.status_code == 200:

            result = response.json()

            st.write("### HR Buddy")

            st.write(result["answer"])

        else:

            st.error(f"Something went wrong. API returned status {response.status_code}.")