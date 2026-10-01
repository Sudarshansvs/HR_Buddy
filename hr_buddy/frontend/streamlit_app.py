import requests
import streamlit as st
from textwrap import dedent

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="HR Buddy",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Simple, clean header
st.markdown("# 🤖 HR Buddy")
st.markdown("*Your AI-powered HR Buddy*")
st.divider()




# Sidebar for configuration
with st.sidebar:

    st.header("⚙️ Configuration")

    # --------------------------------------------------------
    # KNOWLEDGE SOURCE
    # --------------------------------------------------------

    st.subheader("📚 Knowledge Source")

    uploaded_name = st.session_state.get("uploaded_filename")

    knowledge_options = ["All Documents"]

    if uploaded_name:
        knowledge_options.append(uploaded_name)

    knowledge_source = st.selectbox(
        "Select knowledge source",
        knowledge_options,
        index=0,
        label_visibility="collapsed",
    )

    st.caption(
        "Choose which HR documents should be used for answering questions."
    )

    st.divider()

    # --------------------------------------------------------
    # RAG CONFIGURATION
    # --------------------------------------------------------

    with st.expander("🔍 RAG Settings", expanded=False):

        chunk_size = st.slider(
            "Chunk Size",
            min_value=50,
            max_value=2000,
            value=500,
            step=50,
        )

        chunk_overlap = st.slider(
            "Chunk Overlap",
            min_value=0,
            max_value=500,
            value=100,
            step=10,
        )

        top_k = st.slider(
            "Top K Results",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
        )

    # --------------------------------------------------------
    # LLM CONFIGURATION
    # --------------------------------------------------------

    with st.expander("🧠 LLM Tuning", expanded=False):

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
        )

        max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=500,
            step=100,
        )

        top_p = st.slider(
            "Top P",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            step=0.05,
        )

        frequency_penalty = st.slider(
            "Frequency Penalty",
            min_value=0.0,
            max_value=2.0,
            value=0.0,
            step=0.1,
        )

        presence_penalty = st.slider(
            "Presence Penalty",
            min_value=0.0,
            max_value=2.0,
            value=0.0,
            step=0.1,
        )

    # --------------------------------------------------------
    # DOCUMENT UPLOAD
    # --------------------------------------------------------

    st.divider()

    with st.expander("📄 Upload Document", expanded=False):

        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["txt", "md", "pdf"],
        )

        if uploaded_file is not None:

            # Avoid uploading the same file repeatedly
            if (
                st.session_state.get("last_uploaded_file")
                != uploaded_file.name
            ):

                with st.spinner("📤 Uploading..."):

                    try:

                        files = {
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                            )
                        }

                        response = requests.post(
                            f"{API_URL}/api/v1/documents/upload",
                            files=files,
                            timeout=60,
                        )

                        response.raise_for_status()

                        data = response.json()

                        st.session_state.uploaded_filename = data.get(
                            "filename",
                            uploaded_file.name,
                        )

                        st.session_state.last_uploaded_file = (
                            uploaded_file.name
                        )

                        st.success(
                            f"✅ {data.get('message', 'Uploaded successfully')}"
                        )

                        preview = data.get("preview", "")

                        if preview:

                            with st.expander(
                                "Preview",
                                expanded=False,
                            ):
                                st.text(preview[:500])

                        # Refresh so new document appears
                        # in Knowledge Source selector.
                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"❌ Upload failed: {error}"
                        )


active_settings_html = dedent(
    f"""<style>

    .hr-settings-container {{
        position: fixed;
        top: 18px;
        right: 70px;
        z-index: 999999;
        font-family: Arial, sans-serif;
    }}

    .hr-settings-trigger {{
        display: flex;
        align-items: center;
        gap: 7px;
        cursor: pointer;
        padding: 7px 10px;
        border-radius: 8px;
        color: #f5f5f5;
        font-size: 14px;
        font-weight: 500;
        background: transparent;
        transition: background 0.2s ease;
    }}

    .hr-settings-trigger:hover {{
        background: rgba(255, 255, 255, 0.08);
    }}

    .hr-settings-icon {{
        font-size: 20px;
    }}

    .hr-settings-popup {{
        visibility: hidden;
        opacity: 0;
        position: absolute;
        right: 0;
        top: 42px;

        width: 300px;

        padding: 16px;

        background: #1f2129;
        color: #f5f5f5;

        border: 1px solid #3b3d46;
        border-radius: 12px;

        box-shadow:
            0 12px 30px rgba(0, 0, 0, 0.45);

        transition:
            opacity 0.18s ease,
            visibility 0.18s ease;

        font-size: 13px;
        line-height: 1.5;
    }}

    .hr-settings-container:hover .hr-settings-popup {{
        visibility: visible;
        opacity: 1;
    }}

    .hr-settings-title {{
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid #3b3d46;
    }}

    .hr-settings-section {{
        margin-top: 12px;
    }}

    .hr-settings-section-title {{
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 7px;
    }}

    .hr-settings-row {{
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin: 5px 0;
    }}

    .hr-settings-label {{
        color: #b8bac3;
    }}

    .hr-settings-value {{
        color: #ffffff;
        font-weight: 600;
        text-align: right;
    }}

    </style>


    <div class="hr-settings-container">

        <div class="hr-settings-trigger">

            <span class="hr-settings-icon">⚙️</span>

            <span>Settings</span>

        </div>


        <div class="hr-settings-popup">

            <div class="hr-settings-title">
                ⚙️ Active Settings
            </div>


            <div class="hr-settings-section">

                <div class="hr-settings-section-title">
                    📚 Knowledge Source
                </div>

                <div class="hr-settings-row">

                    <span class="hr-settings-label">
                        Source
                    </span>

                    <span class="hr-settings-value">
                        {knowledge_source}
                    </span>

                </div>

            </div>


            <div class="hr-settings-section">

                <div class="hr-settings-section-title">
                    🔍 RAG
                </div>

                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Chunk Size
                    </span>

                    <span class="hr-settings-value">
                        {chunk_size}
                    </span>
                </div>


                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Chunk Overlap
                    </span>

                    <span class="hr-settings-value">
                        {chunk_overlap}
                    </span>
                </div>


                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Top K
                    </span>

                    <span class="hr-settings-value">
                        {top_k}
                    </span>
                </div>

            </div>


            <div class="hr-settings-section">

                <div class="hr-settings-section-title">
                    🧠 LLM
                </div>


                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Temperature
                    </span>

                    <span class="hr-settings-value">
                        {temperature}
                    </span>
                </div>


                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Max Tokens
                    </span>

                    <span class="hr-settings-value">
                        {max_tokens}
                    </span>
                </div>


                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Top P
                    </span>

                    <span class="hr-settings-value">
                        {top_p}
                    </span>
                </div>


                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Frequency Penalty
                    </span>

                    <span class="hr-settings-value">
                        {frequency_penalty}
                    </span>
                </div>


                <div class="hr-settings-row">
                    <span class="hr-settings-label">
                        Presence Penalty
                    </span>

                    <span class="hr-settings-value">
                        {presence_penalty}
                    </span>
                </div>

            </div>

        </div>

    </div>"""
)


# Streamlit HTML renderer
try:
    st.html(active_settings_html)
except AttributeError:
    # Fallback for older Streamlit versions
    st.markdown(
        active_settings_html,
        unsafe_allow_html=True,
    )

if "messages" not in st.session_state:
    st.session_state.messages = []


# Main chat interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat")
    
    # Chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show sources for assistant messages
            sources = message.get("sources", [])

            if sources:
                with st.expander("📚 View Sources", expanded=False):
                    for idx, source in enumerate(sources, 1):
                        st.markdown(
                            f"**{idx}. {source['document']}**"
                        )

                        content = source.get("content", "")

                        st.caption(
                            content[:150] + "..."
                            if len(content) > 150
                            else content
                        )

                        st.metric(
                            "Relevance Score",
                            f"{source['score']:.2%}"
                        )

# with col2:
    
#     st.subheader("⚙️ Active Settings")

    
#     st.info(
#         f"""
#         **RAG**
#         - Chunk: {chunk_size}
#         - Overlap: {chunk_overlap}
#         - Top K: {top_k}
        
#         **LLM**
#         - Temp: {temperature}
#         - Tokens: {max_tokens}
#         - Top P: {top_p}
#         """
#     )



# Chat input
question = st.chat_input("Ask an HR question...")



if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🤔 HR Buddy is analyzing..."):
            try:
                # Determine whether to restrict to uploaded document
                uploaded_name = st.session_state.get("uploaded_filename")
                document_limit = None
                if "query_scope" in locals() and query_scope.startswith("📎"):
                    document_limit = uploaded_name
                payload = {
                    "question": question,
                    "rag_config": {
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        "top_k": top_k
                    },
                    "llm_config": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p,
                        "frequency_penalty": frequency_penalty,
                        "presence_penalty": presence_penalty
                    },
                    "document": document_limit
                }

                response = requests.post(
                    f"{API_URL}/api/v1/chat",
                    json=payload,
                    timeout=120
                )
                

                response.raise_for_status()

                data = response.json()

                answer = data["answer"]

                # Display answer with formatting
                # st.markdown(answer)

                # answer = data["answer"]
                sources = data.get("sources", [])

                # st.markdown(answer)
                st.success(answer)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    }
                )

                if sources:
                    with st.expander("📚 View Sources", expanded=False):
                        for idx, source in enumerate(sources, 1):
                            if source['score']<=0.1:
                                continue
                            st.info(
                                f"### {idx}. 📄 {source['document']}"
                            )
                            st.caption(
                                source["content"][:300]
                                + ("..." if len(source["content"]) > 300 else "")
                            )

                            st.caption(
                                f"Relevance Score: {source['score']:.2%}"
                            )

                            if idx < len(sources):
                                st.divider()
                            if idx >= 2:
                                break
                # st.session_state.messages.append(
                #     {
                #         "role": "assistant",
                #         "content": answer,
                #         "sources": sources
                #     }
                # )

            except Exception as error:
                st.error(f"❌ Error: {error}")
                st.info("Please ensure the HR Buddy API is running on localhost:8000")