import asyncio
import os

from dotenv import load_dotenv
from fastmcp import Client

load_dotenv()  # reads EXPENSE_MCP_URL and EXPENSE_MCP_API_KEY from your .env file

URL = os.getenv("EXPENSE_MCP_URL")
API_KEY = os.getenv("EXPENSE_MCP_API_KEY")

if not URL or not API_KEY:
    raise SystemExit("Please set EXPENSE_MCP_URL and EXPENSE_MCP_API_KEY in your .env file.")

# Same shape as the local config, but with a URL and a Bearer header instead of a command.
CONFIG = {
    "mcpServers": {
        "expense_remote": {
            "url": URL,
            "transport": "http",
            "headers": {"Authorization": f"Bearer {API_KEY}"},
        }
    }
}


async def main():
    try:
        async with Client(CONFIG) as client:
            tools = await client.list_tools()
            print(f"Connected. {len(tools)} tools found:")
            for tool in tools:
                print(" -", tool.name)

            result = await client.call_tool("list_categories", {})
            print("\nlist_categories ->", result.data)
    except Exception as exc:
        print(f"Could not use the remote server: {type(exc).__name__}: {exc}")
        print("Things to check:")
        print(" - 401: the API key is wrong, expired, or not sent as a Bearer token")
        print(" - 403: the key is valid but your account has no access to this server")
        print(" - 404: the URL is wrong (it must end with /mcp)")
        print(" - Also make sure the server shows as Live on the Horizon Deployments page")
        raise SystemExit(1)


asyncio.run(main())