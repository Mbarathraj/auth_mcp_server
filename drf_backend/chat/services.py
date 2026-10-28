"""
The LLM <-> MCP loop, using Google Gemini.

  prompt --> Gemini --(asks for a function)--> this code calls the MCP server --> result
                ^                                                                  |
                +------------------------------------------------------------------+
  ... repeat until Gemini gives a final text answer.

The website backend is the MCP *client*. Google never sees the MCP API key or the
user's token; it only sees tool names and tool results.
"""
import asyncio

from django.conf import settings
from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MAX_STEPS = 6  # hard cap on tool-call rounds, so a confused model can't loop forever

SYSTEM_PROMPT = (
    "You are a task assistant inside a website. Use the provided tools to read and "
    "manage the signed-in user's own tasks. You can only access this user's data. "
    "Never claim to have done something unless a tool call succeeded. "
    "Be brief and friendly."
)


def _text_of(result) -> str:
    """Join the text parts of an MCP tool result."""
    return "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")


async def _run(prompt: str, user_token: str, llm=None):
    llm = llm or genai.Client(api_key=settings.GEMINI_API_KEY)

    headers = {
        "Authorization": f"Bearer {settings.MCP_API_KEY}",  # who is calling (the website)
        "X-User-Token": user_token,                          # on behalf of which user
    }

    async with streamablehttp_client(settings.MCP_SERVER_URL, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()

            # Describe the MCP tools to Gemini as function declarations.
            # MCP tools already carry a JSON Schema, which Gemini accepts directly.
            listed = await session.list_tools()
            declarations = [
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description or "",
                    parameters_json_schema=t.inputSchema,
                )
                for t in listed.tools
            ]

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=declarations)],
                # We run the loop ourselves so every tool call goes through MCP
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            )

            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
            tools_used: list[str] = []

            for _ in range(MAX_STEPS):
                resp = await llm.aio.models.generate_content(
                    model=settings.GEMINI_MODEL, contents=contents, config=config
                )

                calls = resp.function_calls or []
                if not calls:
                    return (resp.text or "").strip(), tools_used

                # Keep the model's turn exactly as returned (Gemini 3 needs its
                # "thought signatures" sent back with the function results).
                contents.append(resp.candidates[0].content)

                parts = []
                for call in calls:
                    tools_used.append(call.name)
                    try:
                        out = await session.call_tool(call.name, dict(call.args or {}))
                        text = _text_of(out)
                        payload = {"error": text} if out.isError else {"result": text}
                    except Exception as exc:  # tell Gemini, so it can explain to the user
                        payload = {"error": f"Tool failed: {exc}"}
                    parts.append(types.Part.from_function_response(name=call.name, response=payload))

                contents.append(types.Content(role="user", parts=parts))

            return "Sorry, that took too many steps. Please try a simpler request.", tools_used


def run_chat(prompt: str, user_token: str, llm=None):
    """Synchronous entry point used by the Django view. Returns (answer, tools_used)."""
    return asyncio.run(_run(prompt, user_token, llm))
