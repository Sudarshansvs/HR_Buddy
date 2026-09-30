import requests
import streamlit as st


API_URL = "http://localhost:8000"


st.set_page_config(
    page_title="HR Buddy",
    page_icon="🤖",
    layout="wide"
)


st.title("🤖 HR Buddy")

st.caption(
    "Your AI-powered HR knowledge assistant"
)


# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ RAG Configuration")
    
    chunk_size = st.slider(
        "Chunk Size",
        min_value=50,
        max_value=2000,
        value=500,
        step=50,
        help="Size of text chunks for processing"
    )
    
    chunk_overlap = st.slider(
        "Chunk Overlap",
        min_value=0,
        max_value=500,
        value=100,
        step=10,
        help="Overlap between consecutive chunks"
    )
    
    top_k = st.slider(
        "Top K Results",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="Number of top results to retrieve"
    )
    
    st.divider()
    st.caption(
        "Adjust these parameters to fine-tune "
        "the retrieval and response quality"
    )


if "messages" not in st.session_state:

    st.session_state.messages = []


# Main chat area
col1, col2 = st.columns([3, 1])

with col1:
    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )


with col2:
    st.info(
        f"**Current Settings**\n\n"
        f"Chunk Size: `{chunk_size}`\n\n"
        f"Overlap: `{chunk_overlap}`\n\n"
        f"Top K: `{top_k}`"
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
                        "question": question,
                        "rag_config": {
                            "chunk_size": chunk_size,
                            "chunk_overlap": chunk_overlap,
                            "top_k": top_k
                        }
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