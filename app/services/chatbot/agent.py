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

    # Fast direct SQL retrieval path for instant price & mandi queries
    msg_lower = user_message.lower()
    if any(kw in msg_lower for kw in ["price", "mandi", "onion", "soybean", "cotton", "wheat", "nashik", "pune", "latur", "rate", "cost", "market"]):
        try:
            # Build fast SQL query based on keywords joining mandis table
            where_clauses = []
            if "onion" in msg_lower:
                where_clauses.append("LOWER(mp.commodity_name) LIKE '%onion%'")
            elif "soybean" in msg_lower:
                where_clauses.append("LOWER(mp.commodity_name) LIKE '%soybean%'")
            elif "cotton" in msg_lower:
                where_clauses.append("LOWER(mp.commodity_name) LIKE '%cotton%'")
            elif "wheat" in msg_lower:
                where_clauses.append("LOWER(mp.commodity_name) LIKE '%wheat%'")

            if "nashik" in msg_lower:
                where_clauses.append("LOWER(m.district) LIKE '%nashik%'")
            elif "pune" in msg_lower:
                where_clauses.append("LOWER(m.district) LIKE '%pune%'")
            elif "latur" in msg_lower:
                where_clauses.append("LOWER(m.district) LIKE '%latur%'")

            where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            fast_sql = f"SELECT mp.commodity_name, mp.modal_price, mp.min_price, mp.max_price, m.district, m.name as mandi_name, mp.arrival_date FROM mandi_prices mp JOIN mandis m ON mp.mandi_id = m.id{where_str} ORDER BY mp.arrival_date DESC LIMIT 10"
            
            res_dict = run_query(engine, fast_sql)
            rows = res_dict.get("rows", [])
            if rows:
                summary = "; ".join(f"{r.get('commodity_name')}: Modal ₹{r.get('modal_price')}/q ({r.get('district') or 'Maharashtra'}, {r.get('arrival_date')})" for r in rows[:4])
                return {
                    "answer": f"Maharashtra Mandi market records: {summary}.",
                    "sql": fast_sql,
                    "columns": res_dict.get("columns"),
                    "rows": rows,
                    "truncated": False,
                    "executions": [{"sql": fast_sql, "result": res_dict}],
                    "schema_tables": schema_tables,
                }
        except Exception as fast_err:
            print(f"[Fast Chatbot Retrieval Fallback]: {fast_err}")

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
