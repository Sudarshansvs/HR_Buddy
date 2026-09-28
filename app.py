import streamlit as st
import requests


st.set_page_config(
    page_title="HR Buddy",
    page_icon="🤖"
)

st.title("🤖 HR Buddy")

question = st.text_input(
    "Ask your HR question"
)


if st.button("Ask HR Buddy"):

    if not question:

        st.warning("Please enter a question.")

    else:

        response = requests.post(
            "http://127.0.0.1:8000/ask",
            json={
                "question": question
            }
        )

        if response.status_code == 200:

            result = response.json()

            st.write("### HR Buddy")

            st.write(result["answer"])

        else:

            st.error("Something went wrong.")