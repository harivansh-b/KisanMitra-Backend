"""Sql-agent orchestration — LLM writes SQL, executor runs it, loop max 2 turns.

DB-aware chat: model sees live schema, calls query_db, we answer with rows.
"""
from __future__ import annotations

import json

from .executor import run_query
from .prompt import OLLAMA_TOOLS, build_messages
from .schema import get_schema, schema_text


def _extract_tool_calls(message: dict) -> list[dict]:
    """Normalize Ollama / OpenAI tool_calls shapes."""
    tcs = message.get("tool_calls") or []
    # Ollama nests as {function: {name, arguments: {... or json string}}}
    norm = []
    for tc in tcs:
        fn = tc.get("function", tc)
        name = fn.get("name")
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {"sql": args}
        norm.append({"name": name, "args": args, "raw": tc})
    return norm


def chat_once(engine, client, user_message: str, history: list[dict] | None = None) -> dict:
    """One chat turn -> {answer, sql, columns, rows, truncated}.

    - Injects live schema into prompt
    - Up to 2 tool iterations: generate SQL -> execute -> final answer
    """
    history = history or []
    schema = get_schema(engine)
    stext = schema_text(schema)
    messages = build_messages(stext, history, user_message)

    # turn 1: model may call query_db
    msg = client.chat(messages, tools=OLLAMA_TOOLS)
    tcs = _extract_tool_calls(msg)

    executed = []
    if tcs:
        for tc in tcs[:2]:  # cap 2 tool calls
            if tc["name"] != "query_db":
                executed.append({"error": f"unknown tool {tc['name']}"})
                continue
            sql = tc["args"].get("sql", "")
            params = tc["args"].get("params")
            try:
                res = run_query(engine, sql, params)
                executed.append({"sql": sql, "result": res})
                # feed back as tool result and ask for final answer
                messages.append(msg)
                messages.append({
                    "role": "tool",
                    "content": json.dumps({"sql": sql, **res}, default=str)[:8000],
                })
            except ValueError as e:
                executed.append({"sql": sql, "error": str(e)})
                messages.append(msg)
                messages.append({"role": "tool", "content": json.dumps({"error": str(e)})})

        # turn 2: final answer grounded on tool results
        final = client.chat(messages)  # no tools second pass — force answer
        answer = (final.get("content") or "").strip() or _fallback_answer(executed)
    else:
        # no tool call — direct answer (greeting / out-of-scope)
        answer = (msg.get("content") or "").strip()
        if not answer:
            answer = "Ask me about mandis, prices, buyers, lots, auctions — I will query the database for you."

    primary = executed[0] if executed else {}
    return {
        "answer": answer,
        "sql": primary.get("sql"),
        "columns": (primary.get("result") or {}).get("columns"),
        "rows": (primary.get("result") or {}).get("rows"),
        "truncated": (primary.get("result") or {}).get("truncated", False),
        "executions": executed,
        "schema_tables": schema.get("table_names", []),
    }


def _fallback_answer(executed: list[dict]) -> str:
    if not executed:
        return ""
    e = executed[0]
    if "error" in e:
        return f"Query failed: {e['error']}"
    r = e.get("result", {})
    if not r.get("rows"):
        return "No rows found for that query."
    return f"Found {r.get('rowcount')} row(s)."
