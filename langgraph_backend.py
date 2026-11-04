from dotenv import load_dotenv
load_dotenv()
from langgraph.graph import StateGraph,START,END, add_messages
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv

import os
import sqlite3


llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY")
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState) -> ChatState:

    messages = state['messages']

    response = llm.invoke(messages)

    return {'messages': [response]}

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

#*****************************CHAT TITLE DATABASE*****************************

conn.execute("""
    CREATE TABLE IF NOT EXISTS chat_titles (
        thread_id TEXT PRIMARY KEY,
        title TEXT
    )
""")

conn.commit()


def save_chat_title(thread_id, title):
    conn.execute(
        "INSERT OR REPLACE INTO chat_titles (thread_id, title) VALUES (?, ?)",
        (thread_id, title)
    )
    conn.commit()


def retrieve_chat_titles():
    cursor = conn.execute("SELECT thread_id, title FROM chat_titles")
    return dict(cursor.fetchall())

graph = StateGraph(ChatState)

#add nodes to the graph
graph.add_node('chat_node',chat_node)

#add edges to the graph
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)