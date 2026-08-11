"""Anthropic Claude API client with tool-use loop.

Sends conversation to Claude, executes tool calls locally against the
SQLite database, and continues until Claude stops with a text response.
"""
import json
from pathlib import Path
from typing import Any

import anthropic

import tools as _tools

# RAG docs loaded at startup — provide game rules context in the system prompt
_RAG_DIR: Path | None = None
_SYSTEM_PROMPT: str = ""

_CONTEXT_ALERTS = {
    "Morrowind": ["smithing", "creation club", "hearthfire", "sigil stone"],
    "Oblivion": ["smithing", "hearthfire", "creation club"],
    "Skyrim": [],  # all systems present
}


def set_rag_dir(rag_dir: Path) -> None:
    """Load RAG markdown docs and build the system prompt."""
    global _RAG_DIR, _SYSTEM_PROMPT
    _RAG_DIR = rag_dir
    docs = []
    for md_file in sorted(rag_dir.glob("*.md")):
        docs.append(f"## {md_file.stem}\n\n{md_file.read_text(encoding='utf-8')}")
    _SYSTEM_PROMPT = (
        "You are GameTools TES Assistant, an expert on The Elder Scrolls crafting systems "
        "(Morrowind, Oblivion, Skyrim). You have access to a SQLite database via tools. "
        "Use tools to answer questions precisely — never invent numbers.\n\n"
        "Rules and mechanics for each game are provided below.\n\n"
        + "\n\n---\n\n".join(docs)
    )


def _context_check(user_message: str, game_context: str) -> str | None:
    """Return a warning string if the query seems off for the current game context, else None."""
    if not game_context or game_context == "All Games":
        return None
    alerts = _CONTEXT_ALERTS.get(game_context, [])
    lower = user_message.lower()
    triggered = [kw for kw in alerts if kw in lower]
    if triggered:
        return (
            f"⚠️ **Context mismatch**: Your current game context is **{game_context}**, "
            f"but your query mentions {', '.join(repr(k) for k in triggered)}, "
            f"which {'is' if len(triggered) == 1 else 'are'} not available in {game_context}. "
            f"Did you mean to ask about Skyrim, or would you like to change the game context?"
        )
    return None


def chat(
    messages: list[dict],
    api_key: str,
    game_context: str = "",
    model: str = "claude-sonnet-5-20251101",
    max_tool_rounds: int = 15,
) -> dict:
    """Run a full tool-use conversation loop.

    Parameters
    ----------
    messages:
        Prior conversation in Anthropic format (alternating user/assistant).
    api_key:
        Anthropic API key.
    game_context:
        Active game context string ("Morrowind", "Oblivion", "Skyrim", or "").
    model:
        Anthropic model ID to use.
    max_tool_rounds:
        Safety cap on tool-use iterations.

    Returns
    -------
    dict with keys:
        "response"    → final assistant text
        "tool_calls"  → list of {name, arguments, result} for each tool used
        "warning"     → context mismatch warning string or None
        "error"       → error string or None
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Build system prompt, injecting game context if set
    system = _SYSTEM_PROMPT
    if game_context and game_context != "All Games":
        system += (
            f"\n\n## Active Game Context\n\nThe user is currently playing **{game_context}**. "
            f"Unless the question explicitly mentions another game, assume all queries refer to {game_context}."
        )

    # Context mismatch check on the latest user message
    warning: str | None = None
    if messages:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        if isinstance(last_user, str):
            warning = _context_check(last_user, game_context)

    tool_calls_log: list[dict] = []
    conv = list(messages)  # working copy

    for _round in range(max_tool_rounds):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                tools=_tools.TOOLS,
                messages=conv,
            )
        except anthropic.AuthenticationError:
            return {
                "response": "",
                "tool_calls": tool_calls_log,
                "warning": warning,
                "error": "Invalid API key. Please update your credentials in Settings.",
            }
        except anthropic.APIError as exc:
            return {
                "response": "",
                "tool_calls": tool_calls_log,
                "warning": warning,
                "error": f"API error: {exc}",
            }

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            return {
                "response": text,
                "tool_calls": tool_calls_log,
                "warning": warning,
                "error": None,
            }

        if response.stop_reason == "tool_use":
            # Add assistant message with all content blocks
            conv.append({
                "role": "assistant",
                "content": [block.model_dump() for block in response.content],
            })

            # Execute each tool call and collect results
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                tool_name = block.name
                arguments = block.input if isinstance(block.input, dict) else {}
                result = _tools.call_tool(tool_name, arguments)
                tool_calls_log.append({
                    "name": tool_name,
                    "arguments": arguments,
                    "result": result,
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })

            conv.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason
        text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        return {
            "response": text or f"(Stopped: {response.stop_reason})",
            "tool_calls": tool_calls_log,
            "warning": warning,
            "error": None,
        }

    return {
        "response": "",
        "tool_calls": tool_calls_log,
        "warning": warning,
        "error": f"Reached maximum tool-use rounds ({max_tool_rounds}) without a final answer.",
    }
