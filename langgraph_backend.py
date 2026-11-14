from dotenv import load_dotenv
load_dotenv()
from rag_pipeline import retrieve_documents
from rag_store import get_vector_store

import os
import sqlite3
import requests
import calendar
from datetime import date, timedelta
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

from mcp_tools import load_expense_tools


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

# ***************************** RAG TOOL (DOCUMENT RETRIEVAL) *****************************

@tool
def search_uploaded_document(query: str) -> str:
    """
    Search the uploaded PDF document and return relevant information.
    Use this tool when the user asks questions about their uploaded document.
    """

    try:

        vector_store = get_vector_store()

        if vector_store is None:
            return "No PDF document has been uploaded yet."

        relevant_documents = retrieve_documents(
            vector_store,
            query
        )

        if not relevant_documents:
            return "No relevant information found in the uploaded document."

        context = "\n\n".join(
            document.page_content
            for document in relevant_documents
        )

        return context

    except Exception as e:

        return f"Document retrieval failed: {str(e)}"


# ***************************** MCP TOOLS (EXPENSE TRACKER) *****************************
# Loaded from the expense tracker MCP server chosen by MCP_MODE in your .env file.
# If the server is not configured or not reachable, this list is empty and the
# chatbot works exactly as before.
expense_tools = load_expense_tools()

# ***************************** AVAILABLE TOOLS *****************************

tools = [
    calculator,
    get_stock_price,
    web_search,
    search_uploaded_document
] + expense_tools

llm_with_tools = llm.bind_tools(tools)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


BASE_PROMPT = """
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
When answering questions about uploaded documents:

1. Use search_uploaded_document to retrieve relevant information from the uploaded PDF.
2. Base your answer on the retrieved document content.
3. Do not invent information that is not present in the document.
4. If relevant information is not found, clearly tell the user.
5. Explain the answer in simple and clear language.
"""

EXPENSE_PROMPT = """
You can also manage the user's personal expense tracker with the expense tools
(add_expense, list_expenses, search_expenses, edit_expense, delete_expense,
summary, monthly_report, budget_status, list_categories and so on).

When using the expense tools:

1. Amounts are in PKR. Today's date is {today}.
2. Dates use the YYYY-MM-DD format and months use YYYY-MM.
3. "This month" is {month} (from {month_start} to {month_end}) and "last month" is {last_month}.
   Use exactly these values and never guess a date range. For a question about one whole
   month, call monthly_report with that month.
4. If you are not sure about a category or subcategory name, call list_categories first.
5. Only report expense data that the tools actually returned. Never invent entries or totals.
6. Ask the user to confirm before calling delete_expense or delete_category.
7. If a tool returns an error, explain it simply and try to fix it, for example by using the right category name.
8. Never create a category or subcategory on your own. If the one the user names does not exist, tell the user, list the existing ones, and ask whether to create it or use another.
"""


def build_system_prompt(today=None) -> str:
    prompt = BASE_PROMPT
    if expense_tools:
        today = today or date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]
        previous_month = today.replace(day=1) - timedelta(days=1)
        prompt += EXPENSE_PROMPT.format(
            today=today.isoformat(),
            month=today.strftime("%Y-%m"),
            month_start=today.replace(day=1).isoformat(),
            month_end=today.replace(day=last_day).isoformat(),
            last_month=previous_month.strftime("%Y-%m"),
        )
    return prompt


def chat_node(state: ChatState) -> ChatState:

    messages = state['messages']

    system_message = SystemMessage(content=build_system_prompt())

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