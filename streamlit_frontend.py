
import tempfile
import os
from rag_store import set_vector_store
from rag_pipeline import process_pdf

import streamlit as st
from langgraph_backend import (
    chatbot,
    retrieve_all_threads,
    save_chat_title,
    retrieve_chat_titles
)
from langchain_core.messages import HumanMessage, AIMessage
import uuid


# ***************************** UTILITY FUNCTIONS *****************************

def generate_thread_id():
    thread_id = str(uuid.uuid4())
    return thread_id


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []


def add_thread(thread_id):
    if thread_id not in st.session_state['chat_thread']:
        st.session_state['chat_thread'].append(thread_id)


def load_conversation_history(thread_id):
    state = chatbot.get_state(
        config={'configurable': {'thread_id': thread_id}}
    )

    return state.values.get('messages', [])


def generate_chat_title(message):
    if message is None:
        return "New Chat"

    title = " ".join(message.strip().split())

    if len(title) > 30:
        title = title[:30] + "..."

    return title


# ***************************** SESSION SETUP *****************************

if "message_history" not in st.session_state:
    st.session_state['message_history'] = []

if "thread_id" not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_thread' not in st.session_state:
    st.session_state['chat_thread'] = retrieve_all_threads()

if "thread_titles" not in st.session_state:
    st.session_state['thread_titles'] = retrieve_chat_titles()

add_thread(st.session_state['thread_id'])


# ***************************** RAG SESSION STATE *****************************

if "vector_store" not in st.session_state:
    st.session_state["vector_store"] = None

if "uploaded_file_name" not in st.session_state:
    st.session_state["uploaded_file_name"] = None


# ***************************** SIDEBAR *****************************

st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("Conversation History")


# ***************************** RAG DOCUMENT UPLOAD *****************************

st.sidebar.divider()

st.sidebar.subheader("📄 Upload Documents")

uploaded_file = st.sidebar.file_uploader(
    "Upload a PDF",
    type=["pdf"]
)


# ***************************** PROCESS UPLOADED PDF *****************************

if uploaded_file is not None:

    # Check whether this PDF is already processed
    if uploaded_file.name != st.session_state["uploaded_file_name"]:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temporary_file:

            temporary_file.write(uploaded_file.getvalue())

            pdf_path = temporary_file.name

        try:

            with st.spinner("Processing PDF..."):

                vector_store = process_pdf(pdf_path)

                st.session_state["vector_store"] = vector_store

                set_vector_store(vector_store)

                st.session_state["uploaded_file_name"] = uploaded_file.name

            st.success("PDF processed successfully!")

        except Exception as e:

            st.error(f"Error processing PDF: {e}")

        finally:

            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    else:

        st.info("This PDF is already processed.")

else:

    st.session_state["vector_store"] = None

    st.session_state["uploaded_file_name"] = None

    set_vector_store(None)


# ***************************** CONVERSATION HISTORY *****************************

for thread_id in st.session_state['chat_thread'][::-1]:

    title = st.session_state['thread_titles'].get(
        thread_id, "New Chat"
    )

    if st.sidebar.button(title, key=thread_id):

        st.session_state['thread_id'] = thread_id

        messages = load_conversation_history(thread_id)

        temporary_message_history = []

        for message in messages:

            # Show user messages
            if isinstance(message, HumanMessage):

                temporary_message_history.append({
                    "role": "user",
                    "content": message.content
                })

            # Show only final AI responses
            elif isinstance(message, AIMessage):

                if not message.tool_calls and message.content:

                    temporary_message_history.append({
                        "role": "assistant",
                        "content": message.content
                    })

        st.session_state['message_history'] = temporary_message_history


# ***************************** MAIN UI *****************************

# Loading the conversation history
for message in st.session_state['message_history']:

    with st.chat_message(message["role"]):
        st.text(message["content"])


user_input = st.chat_input("Type your message here...")

if user_input:

    st.session_state['message_history'].append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.text(user_input)

    # Generate title from first message
    if st.session_state['thread_id'] not in st.session_state['thread_titles']:

        title = generate_chat_title(user_input)

        st.session_state['thread_titles'][st.session_state['thread_id']] = title

        save_chat_title(st.session_state['thread_id'], title)

    CONFIG = {
        'configurable': {
            'thread_id': st.session_state['thread_id']
        },
        'metadata': {
            'thread_id': st.session_state['thread_id']
        },
        'run_name': 'chat_turn'
    }


# ***************************** STREAMING RESPONSE *****************************

if user_input:

    with st.chat_message("assistant"):

        final_answer = ""

        with st.status("Processing your request...", expanded=True) as status:

            for update in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="updates"
            ):

                # Check chatbot node
                if "chat_node" in update:

                    messages = update["chat_node"].get("messages", [])

                    if messages:

                        ai_message = messages[-1]

                        # Detect tool calls
                        tool_calls = getattr(ai_message, "tool_calls", [])

                        if tool_calls:

                            for tool_call in tool_calls:
                                tool_name = tool_call.get("name", "Unknown tool")

                                status.write(
                                    f"Calling **{tool_name}** tool..."
                                )

                        else:

                            content = ai_message.content

                            if isinstance(content, str):
                                final_answer = content

                # Detect tool execution completion
                if "tools" in update:
                    status.write("Tool execution completed.")

            status.update(
                label="Response generated",
                state="complete",
                expanded=False
            )

        st.markdown(final_answer)

    st.session_state['message_history'].append({
        "role": "assistant",
        "content": final_answer
    })
