"""Sql-agent orchestration — lazy schema discovery (LangChain SQLDatabaseToolkit-style).

Flow: list_tables -> get_table_info(1-3) -> [explain_query] -> query_db -> answer.
Loop up to 4 LLM turns, 3 tool calls per turn. No upfront 6k DDL dump.
"""
from __future__ import annotations

import json

from .executor import run_query
from .prompt import OLLAMA_TOOLS, build_messages_lazy
from .schema import get_schema


def _extract_tool_calls(message: dict) -> list[dict]:
    tcs = message.get("tool_calls") or []
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


def _dispatch(engine, name: str, args: dict) -> dict:
    if name == "list_tables":
        from .tools import list_tables
        return list_tables(engine)
    if name == "get_table_info":
        from .tools import get_table_info
        return get_table_info(engine, args.get("table", ""))
    if name == "explain_query":
        from .tools import explain_query
        return explain_query(engine, args.get("sql", ""))
    if name == "query_db":
        sql = args.get("sql", "")
        params = args.get("params")
        res = run_query(engine, sql, params)
        return {"sql": sql, **res}
    return {"error": f"unknown tool {name}"}


def chat_once(engine, client, user_message: str, history: list[dict] | None = None) -> dict:
    """One chat turn -> {answer, sql, columns, rows, truncated, executions}."""
    history = history or []
    schema_tables = get_schema(engine).get("table_names", [])
    hint = f"Available tables: {', '.join(schema_tables)} — call list_tables then get_table_info for relevant ones."

    messages = build_messages_lazy(history, user_message, table_hint=hint)
    executed: list[dict] = []
    last_msg = None
    MAX_TURNS = 4

    for _ in range(MAX_TURNS):
        msg = client.chat(messages, tools=OLLAMA_TOOLS)
        last_msg = msg
        tcs = _extract_tool_calls(msg)
        if not tcs:
            break  # LLM answered directly
        # cap 3 tool calls per turn
        messages.append(msg)
        has_query = False
        for tc in tcs[:3]:
            name = tc["name"]
            args = tc["args"]
            try:
                result = _dispatch(engine, name, args)
                if name == "query_db":
                    executed.append({"sql": args.get("sql", ""), "result": result})
                    has_query = True
                elif "error" in result and name != "query_db":
                    executed.append({"tool": name, "error": result["error"]})
                else:
                    executed.append({"tool": name, "result": result})
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result, default=str)[:8000],
                })
            except ValueError as e:
                executed.append({"tool": name, "sql": args.get("sql", ""), "error": str(e)})
                messages.append({"role": "tool", "content": json.dumps({"error": str(e)})})
            except Exception as e:
                executed.append({"tool": name, "error": str(e)[:500]})
                messages.append({"role": "tool", "content": json.dumps({"error": str(e)[:500]})})
        # if this turn had a query_db, give LLM a chance to answer next turn
        # continue loop so next iteration can be final answer
        if has_query:
            # peek next turn — if LLM already queued more tools we loop; else next iter returns answer
            continue

    # final answer: if last turn was tool calls, ask for grounded summary
    if last_msg is not None and _extract_tool_calls(last_msg):
        final = client.chat(messages)
        answer = (final.get("content") or "").strip() or _fallback_answer(executed)
    else:
        answer = ((last_msg or {}).get("content") or "").strip()
        if not answer:
            answer = _fallback_answer(executed) or "Ask me about mandis, prices, buyers, lots, auctions — I will query the database for you."

    # primary = first query_db result for backwards compat
    primary = next((e for e in executed if "result" in e and "sql" in e), {})
    return {
        "answer": answer,
        "sql": primary.get("sql"),
        "columns": (primary.get("result") or {}).get("columns"),
        "rows": (primary.get("result") or {}).get("rows"),
        "truncated": (primary.get("result") or {}).get("truncated", False),
        "executions": executed,
        "schema_tables": schema_tables,
    }


def _fallback_answer(executed: list[dict]) -> str:
    q = next((e for e in executed if "result" in e and "sql" in e), None)
    if q and "error" in q:
        return f"Query failed: {q['error']}"
    if q:
        r = q.get("result", {})
        if not r.get("rows"):
            return "No rows found for that query."
        return f"Found {r.get('rowcount')} row(s)."
    err = next((e for e in executed if "error" in e), None)
    if err:
        return f"Tool error: {err['error']}"
    return ""
