import asyncio

from fastmcp import Client

# Same idea as claude_desktop_config.json: a name plus the command that starts the server.
UV = r"C:\Users\gh\AppData\Local\Programs\Python\Python310\Scripts\uv.exe"
EXPENSE_DIR = r"C:\Users\gh\Desktop\Fastmcp_expense_tracker"

CONFIG = {
    "mcpServers": {
        "expense_local": {
            "command": UV,
            "args": ["run", "--directory", EXPENSE_DIR, "fastmcp", "run", "main.py"],
        }
    }
}


async def main():
    async with Client(CONFIG) as client:
        tools = await client.list_tools()
        print(f"Connected. {len(tools)} tools found:")
        for tool in tools:
            print(" -", tool.name)

        result = await client.call_tool("list_categories", {})
        print("\nlist_categories ->", result.data)


asyncio.run(main())