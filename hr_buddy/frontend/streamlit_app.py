import requests
import streamlit as st


API_URL = "http://localhost:8000"


st.set_page_config(
    page_title="HR Buddy",
    page_icon="🤖",
    layout="centered"
)


st.title("🤖 HR Buddy")

st.caption(
    "Your AI-powered HR knowledge assistant"
)


if "messages" not in st.session_state:

    st.session_state.messages = []


for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


question = st.chat_input(
    "Ask an HR question..."
)


if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner(
            "HR Buddy is thinking..."
        ):

            try:

                response = requests.post(
                    f"{API_URL}/api/v1/chat",
                    json={
                        "question": question
                    },
                    timeout=120
                )

                response.raise_for_status()

                data = response.json()

                answer = data["answer"]

                st.markdown(answer)

                sources = data.get(
                    "sources",
                    []
                )

                if sources:

                    st.markdown(
                        "### 📚 Sources"
                    )

                    for source in sources:

                        st.caption(
                            f"📄 "
                            f"{source['document']} "
                            f"| Score: "
                            f"{source['score']:.3f}"
                        )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )

            except Exception as error:

                st.error(
                    f"Unable to process request: "
                    f"{error}"
                )