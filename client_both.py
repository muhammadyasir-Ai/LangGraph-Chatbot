import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import Client

load_dotenv()

# FastMCP logs a harmless INFO note when one client talks to two servers; hide it.
logging.getLogger("fastmcp").setLevel(logging.WARNING)

URL = os.getenv("EXPENSE_MCP_URL")
API_KEY = os.getenv("EXPENSE_MCP_API_KEY")
if not URL or not API_KEY:
    raise SystemExit("Please set EXPENSE_MCP_URL and EXPENSE_MCP_API_KEY in your .env file.")

UV = r"C:\Users\gh\AppData\Local\Programs\Python\Python310\Scripts\uv.exe"
EXPENSE_DIR = r"C:\Users\gh\Desktop\Fastmcp_expense_tracker"

# One client, two servers. The server names (expense_local / expense_remote) become tool prefixes.
CONFIG = {
    "mcpServers": {
        "expense_local": {
            "command": UV,
            "args": ["run", "--directory", EXPENSE_DIR, "fastmcp", "run", "main.py"],
        },
        "expense_remote": {
            "url": URL,
            "transport": "http",
            "headers": {"Authorization": f"Bearer {API_KEY}"},
        },
    }
}


async def main():
    try:
        async with Client(CONFIG) as client:
            tools = await client.list_tools()
            names = [tool.name for tool in tools]

            # With two servers, a server that fails to connect is skipped silently,
            # so check that each one really gave us tools.
            servers = ("expense_local", "expense_remote")
            for server in servers:
                count = sum(name.startswith(server + "_") for name in names)
                print(f"{server}: {count} tools" if count else f"{server}: NO TOOLS (connection failed)")
            if not all(any(n.startswith(s + "_") for n in names) for s in servers):
                raise RuntimeError("one of the servers did not connect")

            print(f"\nConnected to both servers. {len(names)} tools in total:")
            for name in names:
                print(" -", name)

            # Same tool, two servers, two separate databases.
            for server in servers:
                result = await client.call_tool(f"{server}_list_categories", {})
                print(f"\n{server}_list_categories ->", sorted(result.data))
    except Exception as exc:
        print(f"Could not connect to both servers: {type(exc).__name__}: {exc}")
        print("Run client_local.py and client_remote.py separately to see which one fails.")
        raise SystemExit(1)


asyncio.run(main())