
import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage
import uuid

#*****************************UTILITY FUNCTIONS*****************************
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
    return state.values['messages']

#***************************SESSION SETUP***************************
if "message_history" not in st.session_state:
    st.session_state['message_history'] = []

if "thread_id" not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_thread' not in st.session_state:
    st.session_state['chat_thread'] = []

add_thread(st.session_state['thread_id'])

#**************************SIDEBAR******************************
#**************************SIDEBAR******************************
st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("Conversation History")

for thread_id in st.session_state['chat_thread'][::-1]:
    if st.sidebar.button(thread_id):
        st.session_state['thread_id'] = thread_id

        messages = load_conversation_history(thread_id)

        temporary_message_history = []

        for message in messages:
            if isinstance(message, HumanMessage):
                role = "user"
            else:
                role = "assistant"

            temporary_message_history.append({
                "role": role,
                "content": message.content
            })

        st.session_state['message_history'] = temporary_message_history
                 

#******************************MAIN UI******************************
#loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state['message_history'].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

CONFIG = {'configurable': {'thread_id': st.session_state['thread_id'] }}


#***************************STREAMING RESPONSE***************************

#Displays AI responses in real time, instead of waiting for the complete response.
#***************************STREAMING RESPONSE***************************

# Displays AI responses in real time
if user_input:

    with st.chat_message("assistant"):
        ai_message = st.write_stream(
            message_chunk.content
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            )
        )

    st.session_state['message_history'].append(
        {"role": "assistant", "content": ai_message}
    )
