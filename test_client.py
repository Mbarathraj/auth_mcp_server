"""
Calls the MCP server directly (no LLM involved).

Usage (PowerShell):
  $env:USER_TOKEN = "<access token from POST /api/token/>"
  python test_client.py
"""
import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()
URL = os.environ.get("MCP_URL", "http://127.0.0.1:8001/mcp")
HEADERS = {
    "Authorization": f"Bearer {os.environ['MCP_API_KEY']}",
    "X-User-Token": os.environ.get("USER_TOKEN", ""),
}


async def main():
    async with streamablehttp_client(URL, headers=HEADERS) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            result = await session.call_tool("list_my_tasks", {})
            print("list_my_tasks ->", result.content[0].text if result.content else "[]")


asyncio.run(main())
