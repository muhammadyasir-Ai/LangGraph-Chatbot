from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
import requests
from typing import TypedDict, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from ddgs import DDGS
from langchain_core.messages import SystemMessage


llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY")
)

@tool
def web_search(query: str) -> list:
    """Search the web and return source titles, URLs, and snippets."""
    try:
        results = DDGS().text(
            query,
            backend="auto",
            max_results=5
        )

        return [
            {
                "title": item.get("title", ""),
                "link": item.get("href", ""),
                "snippet": item.get("body", "")
            }
            for item in results
        ]

    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {"first_num": first_num, "second_num": second_num,
                "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock quote using Alpha Vantage.
    Example symbols: AAPL, TSLA, IBM.
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        return {"error": "Alpha Vantage API key is missing"}

    try:
        url = "https://www.alphavantage.co/query"

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": api_key
        }

        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()

        return r.json()

    except requests.RequestException as e:
        return {"error": str(e)}


tools = [calculator, get_stock_price, web_search]
llm_with_tools = llm.bind_tools(tools)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]



def chat_node(state: ChatState) -> ChatState:

    messages = state['messages']

    system_message = SystemMessage(content="""
You are a reliable research assistant.

When using web_search:

1. Use ONLY the returned search results.
2. Never invent titles, URLs, dates, model names, or facts.
3. Copy source titles and URLs exactly as returned.
4. Every finding must be directly supported by its snippet.
5. Do not combine information from unrelated sources.
6. If a snippet is insufficient, exclude that finding.
7. Clearly state when information cannot be verified.
8. Never claim that results are the latest unless dates support it.
""")

    response = llm_with_tools.invoke(
        [system_message] + messages
    )

    return {'messages': [response]}


tool_node = ToolNode(tools)

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# ***************************** 6. GRAPH *****************************

tool_node = ToolNode(tools)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")

graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)

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


def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)