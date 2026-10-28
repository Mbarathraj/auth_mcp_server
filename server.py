"""
MCP server that exposes per-user task tools.

Two layers of trust on every request:
  1. Authorization: Bearer <MCP_API_KEY>   -> "this caller is my website backend"
  2. X-User-Token:  <user's JWT access token> -> "...acting for THIS logged-in user"

The tools never accept a user id from the LLM. They forward the user's own JWT
to the Django REST API, and Django decides what that user may see.
"""
import os
import secrets
from contextvars import ContextVar

import httpx
import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

API_KEY = os.environ.get("MCP_API_KEY", "")
if len(API_KEY) < 16:
    raise SystemExit(
        "MCP_API_KEY is missing or too short. Generate one with:\n"
        "  python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
        "and put it in the .env file."
    )

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8001"))  # 8000 is used by the Django backend
DRF_BASE_URL = os.environ.get("DRF_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# Holds the current request's user JWT (set by the middleware below)
current_user_token: ContextVar[str] = ContextVar("current_user_token", default="")

mcp = FastMCP("tasks-server", stateless_http=True, json_response=True)


# --------------------------------------------------------------------------
# Helper: call the Django API as the current user
# --------------------------------------------------------------------------
async def drf(method: str, path: str, **kwargs):
    token = current_user_token.get()
    if not token:
        raise ValueError("No user token was provided, so I cannot act for a user.")

    async with httpx.AsyncClient(base_url=DRF_BASE_URL, timeout=10) as client:
        resp = await client.request(
            method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
        )

    if resp.status_code == 401:
        raise ValueError("The user's session token is invalid or expired.")
    if resp.status_code == 404:
        raise ValueError("That item was not found.")
    resp.raise_for_status()
    return resp.json() if resp.content else None


# --------------------------------------------------------------------------
# Tools (note: none of them takes a user id)
# --------------------------------------------------------------------------
@mcp.tool()
async def list_my_tasks(only_open: bool = False) -> list:
    """List the current user's tasks. Set only_open=true to hide completed ones."""
    tasks = await drf("GET", "/api/tasks/")
    if only_open:
        tasks = [t for t in tasks if not t["is_done"]]
    return tasks


@mcp.tool()
async def create_task(title: str, description: str = "") -> dict:
    """Create a new task for the current user."""
    return await drf("POST", "/api/tasks/", json={"title": title, "description": description})


@mcp.tool()
async def set_task_done(task_id: int, is_done: bool = True) -> dict:
    """Mark one of the current user's tasks as done (or not done) by its id."""
    return await drf("PATCH", f"/api/tasks/{task_id}/", json={"is_done": is_done})


# --------------------------------------------------------------------------
# Middleware: check the API key, then remember the user's token for the tools
# --------------------------------------------------------------------------
class AuthMiddleware:
    def __init__(self, app, api_key: str):
        self.app = app
        self.api_key = api_key.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope["headers"])  # header names are lowercase bytes
        auth = headers.get(b"authorization", b"").decode()
        scheme, _, token = auth.partition(" ")

        ok = scheme.lower() == "bearer" and secrets.compare_digest(
            token.encode(), self.api_key
        )
        if not ok:
            body = b'{"error":"unauthorized","message":"Missing or invalid bearer token"}'
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"www-authenticate", b'Bearer realm="mcp"'),
                    (b"content-length", str(len(body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return

        user_token = headers.get(b"x-user-token", b"").decode()
        reset = current_user_token.set(user_token)
        try:
            await self.app(scope, receive, send)
        finally:
            current_user_token.reset(reset)


app = mcp.streamable_http_app()
app.add_middleware(AuthMiddleware, api_key=API_KEY)

if __name__ == "__main__":
    print(f"MCP server at http://{HOST}:{PORT}/mcp  (forwarding user tokens to {DRF_BASE_URL})")
    uvicorn.run(app, host=HOST, port=PORT)
