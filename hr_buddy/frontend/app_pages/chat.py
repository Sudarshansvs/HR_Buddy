import json
import uuid

import requests
import streamlit as st
from textwrap import dedent

from hr_api import api, error_message

if "messages" not in st.session_state:
    st.session_state.messages = []

# Identifies this chat for short-term memory on the backend
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex


def recent_turns(messages, max_turns=5):
    """Pair up earlier user/assistant messages as turns for short-term memory."""
    turns = [
        {"question": user["content"], "answer": assistant["content"]}
        for user, assistant in zip(messages, messages[1:])
        if user["role"] == "user" and assistant["role"] == "assistant"
    ]
    return turns[-max_turns:]


def run_card_button(message_index, item_index, button):
    """POST a card button's request and record the outcome on the card item."""
    item = st.session_state.messages[message_index]["card"]["items"][item_index]
    try:
        response = api("POST", button["path"], json=button["body"], rerun_on_expiry=False)
        data = response.json()
        item["ok"] = response.ok
        item["result"] = data.get("message") or data.get("detail") or "Done."
    except (requests.RequestException, ValueError) as error:
        item["ok"] = False
        item["result"] = f"Could not reach HR Buddy: {error}"


def render_card(message_index):
    """Show a task card; each item keeps its buttons until one is clicked."""
    card = st.session_state.messages[message_index].get("card")
    if not card:
        return

    for item_index, item in enumerate(card["items"]):
        with st.container(border=True):
            st.markdown(f"**{item['heading']}**")
            st.markdown(
                "\n".join(f"- **{label}:** {value}" for label, value in item["rows"])
            )
            for note in item.get("notes", []):
                st.caption(f":material/info: {note}")

            if "result" in item:
                if item["ok"]:
                    st.success(item["result"], icon=":material/check_circle:")
                else:
                    st.error(item["result"], icon=":material/error:")
                continue

            with st.container(horizontal=True):
                for button_index, button in enumerate(item["buttons"]):
                    st.button(
                        button["label"],
                        key=f"card_{message_index}_{item_index}_{button_index}",
                        type="primary" if button["primary"] else "secondary",
                        on_click=run_card_button,
                        args=(message_index, item_index, button),
                    )


def clear_conversation():
    st.session_state.messages = []
    try:
        api(
            "DELETE",
            f"/api/v1/memory/me/sessions/{st.session_state.session_id}",
            rerun_on_expiry=False,
            timeout=10,
        )
    except requests.RequestException:
        pass


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
    # MEMORY
    # --------------------------------------------------------

    st.divider()

    with st.expander("🧠 Memory", expanded=False):

        st.caption(
            f"Short-term: this chat ({len(st.session_state.messages) // 2} turns)"
        )

        st.button(
            "Clear conversation",
            on_click=clear_conversation,
            width="stretch",
        )

        st.caption("Long-term: what HR Buddy remembers about you")

        try:
            memories = api("GET", "/api/v1/memory/me", timeout=10).json().get("memories", [])
        except requests.RequestException:
            memories = []
            st.warning("Could not load memories.")

        if not memories:
            st.caption("Nothing remembered yet.")

        for memory in memories:
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(f"- {memory['text']}")
                if st.button(
                    ":material/delete:",
                    key=f"forget_{memory['id']}",
                    help="Forget this",
                    type="tertiary",
                ):
                    api("DELETE", f"/api/v1/memory/me/{memory['id']}", timeout=10)
                    st.rerun()

        if memories and st.button("Forget everything", width="stretch"):
            api("DELETE", "/api/v1/memory/me", timeout=10)
            st.rerun()


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

# Main chat interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat")

    
    # Chat history
    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            render_card(message_index)

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
question = st.chat_input("Ask an HR question or apply for leave...")



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
        try:
            # Restrict retrieval to the selected document, if any
            document_limit = (
                None
                if knowledge_source == "All Documents"
                else knowledge_source
            )
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
                "document": document_limit,
                "session_id": st.session_state.session_id,
                # The current question was just appended; send only earlier turns
                "history": recent_turns(st.session_state.messages[:-1])
            }

            with st.spinner("🤔 HR Buddy is analyzing..."):
                response = api(
                    "POST",
                    "/api/v1/chat/stream",
                    json=payload,
                    stream=True,
                    timeout=120
                )
                if not response.ok:
                    raise RuntimeError(error_message(response))

                events = (
                    json.loads(line)
                    for line in response.iter_lines(decode_unicode=True)
                    if line
                )

                # The first event carries the retrieved sources
                first_event = next(events)
                if first_event["type"] == "error":
                    raise RuntimeError(first_event["message"])
                sources = first_event.get("sources", [])
                used_memories = first_event.get("memories", [])

            received = {}

            def token_stream():
                for event in events:
                    if event["type"] == "token":
                        yield event["content"]
                    elif event["type"] == "card":
                        received["card"] = event["card"]
                    elif event["type"] == "error":
                        raise RuntimeError(event["message"])

            answer = st.write_stream(token_stream())

            if used_memories:
                st.caption(
                    f"🧠 Personalised using {len(used_memories)} thing(s) I remember about you"
                )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "card": received.get("card")
                }
            )

            render_card(len(st.session_state.messages) - 1)

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