"""
MCP client bridge for the LangGraph chatbot (written by hand on top of the fastmcp Client,
the same Client you used in client_local.py and client_remote.py).

What it does
    1. Opens ONE connection to the expense tracker and keeps it open while the app runs.
    2. Asks the server for its tools (list_tools).
    3. Wraps each MCP tool as a normal LangChain tool, so the chatbot's ToolNode can call it.

The chatbot is synchronous, but the fastmcp Client is async. So the connection lives on its
own asyncio event loop in a background thread, and the wrapped tools hand their calls to it.

Which server does the chatbot use?  Set MCP_MODE in your .env file:
    MCP_MODE=local    (default) your computer's expense tracker, started with uv
    MCP_MODE=remote   the Horizon server; needs EXPENSE_MCP_URL and EXPENSE_MCP_API_KEY

If the server cannot be reached, the chatbot still starts with its normal tools and prints why.
"""

import asyncio
import atexit
import logging
import os
import threading

from fastmcp import Client
from langchain_core.tools import StructuredTool

# FastMCP prints a banner and INFO logs; keep the chatbot's terminal quiet.
logging.getLogger("fastmcp").setLevel(logging.WARNING)

REQUEST_TIMEOUT = 60  # seconds; the first call to a sleeping remote server can be slow

# --- Local server settings (same command as in claude_desktop_config.json) ---
UV = os.getenv("UV_PATH", r"C:\Users\gh\AppData\Local\Programs\Python\Python310\Scripts\uv.exe")
EXPENSE_DIR = os.getenv("EXPENSE_LOCAL_DIR", r"C:\Users\gh\Desktop\Fastmcp_expense_tracker")


def _local_server() -> dict:
    return {
        "command": UV,
        "args": ["run", "--directory", EXPENSE_DIR, "fastmcp", "run", "main.py"],
    }


def _remote_server():
    url = os.getenv("EXPENSE_MCP_URL")
    api_key = os.getenv("EXPENSE_MCP_API_KEY")
    if not url or not api_key:
        return None
    return {
        "url": url,
        "transport": "http",
        "headers": {"Authorization": f"Bearer {api_key}"},
    }


# --- A background event loop, so sync code can call the async Client ---

_loop = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            threading.Thread(
                target=_loop.run_forever, name="mcp-event-loop", daemon=True
            ).start()
        return _loop


def _run(coro, timeout: float = REQUEST_TIMEOUT):
    return asyncio.run_coroutine_threadsafe(coro, _get_loop()).result(timeout=timeout)


# --- MCP tool -> LangChain tool ---

def _close_client(client: Client) -> None:
    """Close the MCP connection when the app exits, so no background task is left hanging."""
    try:
        _run(client.__aexit__(None, None, None), timeout=5)
    except Exception:
        pass


def _result_text(result) -> str:
    """Join the text blocks of an MCP result into one plain string for the chat model."""
    parts = [block.text for block in result.content if getattr(block, "text", None)]
    return "\n".join(parts)


def _to_langchain_tool(client: Client, tool) -> StructuredTool:
    name = tool.name

    def run(**kwargs):
        # The model sometimes sends null for optional arguments; leave those out.
        arguments = {key: value for key, value in kwargs.items() if value is not None}
        try:
            result = _run(client.call_tool(name, arguments, raise_on_error=False))
        except Exception as exc:  # hand the problem back to the model instead of crashing the graph
            return f"Error from tool '{name}': {exc}"

        text = _result_text(result)
        if result.is_error:
            if text.lower().startswith("error"):
                return text
            return f"Error from tool '{name}': {text or 'unknown error'}"
        return text or str(result.data)

    schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {
        "type": "object", "properties": {}
    }
    return StructuredTool(
        name=name,
        description=tool.description or name,
        args_schema=schema,
        func=run,
    )


def load_expense_tools() -> list:
    """Connect to the expense tracker and return its tools as LangChain tools ([] on failure)."""
    mode = os.getenv("MCP_MODE", "local").strip().lower()

    if mode == "local":
        server = _local_server()
    elif mode == "remote":
        server = _remote_server()
        if server is None:
            print("[mcp_tools] MCP_MODE=remote but EXPENSE_MCP_URL or EXPENSE_MCP_API_KEY "
                  "is missing; starting without expense tools.")
            return []
    else:
        print(f"[mcp_tools] Unknown MCP_MODE '{mode}' (use 'local' or 'remote'); "
              "starting without expense tools.")
        return []

    try:
        client = Client({"mcpServers": {"expense": server}})
        _run(client.__aenter__())          # open the connection and keep it open
        tools = _run(client.list_tools())
    except Exception as exc:
        print(f"[mcp_tools] Could not connect to the {mode} expense server: "
              f"{type(exc).__name__}: {exc}")
        return []

    atexit.register(_close_client, client)
    print(f"[mcp_tools] Connected to the {mode} expense server: {len(tools)} tools.")
    return [_to_langchain_tool(client, tool) for tool in tools]