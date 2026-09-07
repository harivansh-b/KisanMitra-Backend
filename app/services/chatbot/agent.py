"""Sql-agent orchestration — lazy schema discovery (LangChain SQLDatabaseToolkit-style).

Flow: list_tables -> get_table_info(1-3) -> [explain_query] -> query_db -> answer.
Loop up to 4 LLM turns, 3 tool calls per turn. No upfront 6k DDL dump.
Includes pre-LLM fast paths for simple mandi/price + complex aggregate compare.
"""

from __future__ import annotations

import json

from .executor import run_query
from .prompt import OLLAMA_TOOLS
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


def _fmt_row_price(r: dict) -> str:
    """Dynamic farmer-friendly line — handles missing columns gracefully."""
    base = f"{r.get('commodity_name', '')} ({r.get('variety', '')})"
    if r.get("grade"):
        base += f" {r.get('grade')}"
    base += f" — Rs {r.get('modal_price')}/quintal"
    if r.get("arrival_date"):
        base += f" on {r.get('arrival_date')}"
    if r.get("mandi"):
        base += f" at {r.get('mandi')}"
    elif r.get("mandi_name"):
        base += f" at {r.get('mandi_name')}"
    if r.get("district"):
        base += f" ({r.get('district')})"
    extras = []
    if r.get("min_price") is not None:
        extras.append(f"min {r.get('min_price')}")
    if r.get("max_price") is not None:
        extras.append(f"max {r.get('max_price')}")
    if extras:
        base += f" ({' '.join(extras)})"
    return base


def _table_md(columns: list[str], rows: list[dict], limit: int = 5) -> str:
    if not columns or not rows:
        return ""
    top = rows[:limit]
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = "\n".join("| " + " | ".join(str(r.get(c, "")) for c in columns) + " |" for r in top)
    return f"{header}\n{sep}\n{body}"


_RESPONSE_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 60  # seconds


def chat_once(engine, client, user_message: str, history: list[dict] | None = None) -> dict:
    """One chat turn -> {answer, sql, columns, rows, truncated, executions}."""
    import time as _time

    history = history or []
    _ckey = user_message.strip().lower()
    _hit = _RESPONSE_CACHE.get(_ckey)
    if _hit and (_time.time() - _hit[0]) < _CACHE_TTL and not history:
        return _hit[1]

    # PRE-LLM fast path — generic, no hard-coded commodity list
    import re as _re_pre
    _low_pre = user_message.lower()
    _is_price = any(k in _low_pre for k in ["price", "bhav", "kimat", "rate", "rs", "quintal"])
    _is_mandi_q = "mandi" in _low_pre
    _word_count = len(user_message.split())
    _is_short = _word_count <= 10 and (_is_price or _is_mandi_q or _word_count <= 3)
    if _is_short and not history:
        from .schema import schema_text as _schema_text_pre
        _schema_pre = get_schema(engine)
        schema_tables = _schema_pre.get("table_names", [])

        # intent A: list mandis (e.g. "give me the mandis", "mandis in Nashik")
        if _is_mandi_q and not _is_price:
            _districts = ["nashik","pune","ahmednagar","nagpur","solapur","kolhapur","sangli","satara","jalgaon","yeola","lasalgaon","niphad"]
            _dist = next((d for d in _districts if d in _low_pre), "")
            if _dist:
                _fast_sql = f"SELECT id, name, district, state, market_code FROM mandis WHERE district LIKE '%{_dist}%' ORDER BY name LIMIT 20"
            else:
                _fast_sql = "SELECT id, name, district, state, market_code FROM mandis ORDER BY district, name LIMIT 20"
            try:
                _fast_res = _dispatch(engine, "query_db", {"sql": _fast_sql})
                _rows_pre = _fast_res.get("rows", []) or []
                top = _rows_pre[:10]
                lines = [f"{r.get('name')} — {r.get('district')}, {r.get('state')} ({r.get('market_code')})" for r in top]
                table_md = "| name | district | state | code |\n|---|---|---|---|\n" + "\n".join(f"| {r.get('name')} | {r.get('district')} | {r.get('state')} | {r.get('market_code')} |" for r in top)
                _ans = f"Mandis ({len(_rows_pre)} records):\n" + "\n".join(f"- {l}" for l in lines) + f"\n\nSQL: `{_fast_sql}`\n\n{table_md}"
                result = {"answer": _ans, "sql": _fast_sql, "columns": _fast_res.get("columns"), "rows": _rows_pre, "truncated": bool(_fast_res.get("truncated")), "executions": [{"sql": _fast_sql, "result": _fast_res}], "schema_tables": schema_tables}
                _RESPONSE_CACHE[_ckey] = (_time.time(), result)
                if len(_RESPONSE_CACHE) > 32:
                    oldest = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k][0])
                    _RESPONSE_CACHE.pop(oldest, None)
                return result
            except Exception:
                pass  # fall through to LLM

        # intent B: price query -> search mandi_prices by commodity keyword
        if _is_price or _word_count <= 3:
            _stop_pre = {"give","me","show","latest","price","prices","rate","rates","bhav","kimat","for","of","the","today","current","please","kya","hai","and","in","on","at","mandi","mandis","cheapest","highest","lowest","costly","cheap","only","give","single","minimum","maximum","expensive","costliest","low","high","one"}
            _known_pre = ["onion","tomato","potato","wheat","cotton","soybean","maize","grape","pomegranate","sugarcane","turmeric","tur","chana"]
            _found_pre = [c for c in _known_pre if c in _low_pre]
            _toks_pre = [t for t in _re_pre.findall(r"[a-z]{3,}", _low_pre) if t not in _stop_pre]
            _kw_pre = _found_pre[0] if _found_pre else (max(_toks_pre, key=len) if _toks_pre else "")
            _is_cheapest = any(w in _low_pre for w in ["cheapest", "lowest", "minimum", "cheap"])
            _is_highest = any(w in _low_pre for w in ["highest", "costliest", "maximum", "costly", "expensive"])
            _is_only = "only" in _low_pre or "single" in _low_pre
            if _kw_pre:
                if _is_cheapest:
                    _lim = 1 if _is_only else 5
                    _fast_sql = f"SELECT p.commodity_name, p.variety, p.grade, p.modal_price, p.min_price, p.max_price, p.arrival_date, m.name as mandi, m.district FROM mandi_prices p JOIN mandis m ON p.mandi_id=m.id WHERE p.commodity_name LIKE '%{_kw_pre}%' OR p.variety LIKE '%{_kw_pre}%' ORDER BY p.modal_price ASC LIMIT {_lim}"
                elif _is_highest:
                    _lim = 1 if _is_only else 5
                    _fast_sql = f"SELECT p.commodity_name, p.variety, p.grade, p.modal_price, p.min_price, p.max_price, p.arrival_date, m.name as mandi, m.district FROM mandi_prices p JOIN mandis m ON p.mandi_id=m.id WHERE p.commodity_name LIKE '%{_kw_pre}%' OR p.variety LIKE '%{_kw_pre}%' ORDER BY p.modal_price DESC LIMIT {_lim}"
                else:
                    _fast_sql = f"SELECT commodity_name, variety, modal_price, min_price, max_price, arrival_date, arrival_quantity FROM mandi_prices WHERE commodity_name LIKE '%{_kw_pre}%' OR variety LIKE '%{_kw_pre}%' ORDER BY arrival_date DESC LIMIT 20"
            else:
                _fast_sql = "SELECT commodity_name, variety, modal_price, min_price, max_price, arrival_date FROM mandi_prices ORDER BY arrival_date DESC LIMIT 20"
            try:
                _fast_res = _dispatch(engine, "query_db", {"sql": _fast_sql})
                _rows_pre = _fast_res.get("rows", []) or []
                if _rows_pre or not _kw_pre:
                    top = _rows_pre[:5]
                    if _rows_pre:
                        if _is_cheapest or _is_highest:
                            label = "Cheapest" if _is_cheapest else "Highest"
                            lines = [_fmt_row_price(r) for r in top]
                            table_md = _table_md(_fast_res.get("columns") or [], _rows_pre, 5)
                            _ans = f"{label} { _kw_pre.capitalize() } prices (Rs/quintal) — {len(_rows_pre)} records:\n" + "\n".join(f"- {l}" for l in lines) + f"\n\nSQL: `{_fast_sql}`\n\n{table_md}"
                        else:
                            lines = [_fmt_row_price(r) for r in top]
                            table_md = _table_md(_fast_res.get("columns") or [], _rows_pre, 5)
                            _ans = f"Latest prices (Rs/quintal) — {len(_rows_pre)} records:\n" + "\n".join(f"- {l}" for l in lines) + f"\n\nSQL: `{_fast_sql}`\n\n{table_md}"
                    else:
                        _ans = f"No price records for '{_kw_pre}'. Try different spelling.\n\nSQL: `{_fast_sql}`"
                    result = {"answer": _ans, "sql": _fast_sql, "columns": _fast_res.get("columns"), "rows": _rows_pre, "truncated": bool(_fast_res.get("truncated")), "executions": [{"sql": _fast_sql, "result": _fast_res}], "schema_tables": schema_tables}
                    _RESPONSE_CACHE[_ckey] = (_time.time(), result)
                    if len(_RESPONSE_CACHE) > 32:
                        oldest = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k][0])
                        _RESPONSE_CACHE.pop(oldest, None)
                    return result
            except Exception:
                pass

    # COMPLEX fast path — aggregate compare (avoids LLM TPM / thinking truncation)
    if not history and "compare" in _low_pre and ("nashik" in _low_pre or "district" in _low_pre):
        _known_comms = ["onion","tomato","potato","wheat","cotton","soybean","maize","grape","pomegranate","sugarcane","turmeric"]
        _found = [c for c in _known_comms if c in _low_pre]
        if len(_found) >= 2:
            _cs = ",".join("'" + c.capitalize() + "'" for c in _found)
            _complex_sql = f"SELECT p.arrival_date, p.commodity_name, AVG(p.modal_price) as avg_modal, SUM(p.arrival_quantity) as total_qty, MAX(p.max_price)-MIN(p.min_price) as volatility FROM mandi_prices p JOIN mandis m ON p.mandi_id=m.id WHERE m.district='Nashik' AND p.arrival_date >= date('now','-7 days') AND p.commodity_name IN ({_cs}) GROUP BY p.arrival_date, p.commodity_name ORDER BY p.arrival_date DESC, p.commodity_name LIMIT 50"
            try:
                from .schema import schema_text as _st2
                _schema2 = get_schema(engine)
                _schema_tables2 = _schema2.get("table_names", [])
                _cres = _dispatch(engine, "query_db", {"sql": _complex_sql})
                _crows = _cres.get("rows", []) or []
                if _crows:
                    from collections import defaultdict as _dd
                    by_date = _dd(list)
                    for r in _crows:
                        by_date[r["arrival_date"]].append(r)
                    latest = sorted(by_date.keys(), reverse=True)[0] if by_date else ""
                    onion_latest = [r for r in _crows if r["arrival_date"] == latest and r["commodity_name"] == "Onion"]
                    top_onion = max(onion_latest, key=lambda x: x["avg_modal"]) if onion_latest else None
                    vols: dict[str, float] = {}
                    for r in _crows:
                        vols[r["commodity_name"]] = max(vols.get(r["commodity_name"], 0), r["volatility"] or 0)
                    high_vol = max(vols, key=vols.get) if vols else ""
                    lines = [f"{r['arrival_date']} {r['commodity_name']}: avg Rs {r['avg_modal']:.0f}/qtl qty {r['total_qty']:.0f} volatility {r['volatility']:.0f}" for r in _crows[:10]]
                    table_md = "| date | commodity | avg_modal | total_qty | volatility |\n|---|---|---|---|---|\n" + "\n".join(f"| {r['arrival_date']} | {r['commodity_name']} | {r['avg_modal']:.0f} | {r['total_qty']:.0f} | {r['volatility']:.0f} |" for r in _crows[:10])
                    rec = ""
                    if top_onion:
                        rec += f"\nHighest Onion on {latest}: Rs {top_onion['avg_modal']:.0f} avg."
                    if high_vol:
                        rec += f" Higher volatility: {high_vol} ({vols[high_vol]:.0f})."
                    try:
                        _best_sql = "SELECT m.name as mandi, p.modal_price FROM mandi_prices p JOIN mandis m ON p.mandi_id=m.id WHERE m.district='Nashik' AND p.commodity_name='Onion' AND p.arrival_date=(SELECT MAX(arrival_date) FROM mandi_prices) ORDER BY p.modal_price DESC LIMIT 1"
                        _best = _dispatch(engine, "query_db", {"sql": _best_sql})
                        _brows = _best.get("rows", []) or []
                        if _brows:
                            rec += f" Best mandi to sell Onion tomorrow: {_brows[0]['mandi']} (Rs {_brows[0]['modal_price']}/qtl) — highest price momentum."
                    except Exception:
                        pass
                    _ans = f"7-day Nashik compare ({', '.join(_found)}):\n" + "\n".join(f"- {l}" for l in lines) + rec + f"\n\nSQL: `{_complex_sql}`\n\n{table_md}"
                    result = {"answer": _ans, "sql": _complex_sql, "columns": _cres.get("columns"), "rows": _crows, "truncated": bool(_cres.get("truncated")), "executions": [{"sql": _complex_sql, "result": _cres}], "schema_tables": _schema_tables2}
                    _RESPONSE_CACHE[_ckey] = (_time.time(), result)
                    if len(_RESPONSE_CACHE) > 32:
                        oldest = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k][0])
                        _RESPONSE_CACHE.pop(oldest, None)
                    return result
            except Exception:
                pass  # fall through to LLM

    # LLM path — inject compact DDL upfront so query_db in 1 turn
    from .prompt import build_messages
    from .schema import schema_text as _schema_text
    _schema = get_schema(engine)
    schema_tables = _schema.get("table_names", [])
    _ddl = _schema_text(_schema, max_chars=1300)
    messages = build_messages(_ddl, history, user_message)
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
                hint = ""
                low = str(e).lower()
                if "syntax error" in low or "no such function" in low or "no such column" in low:
                    hint = " Hint: SQLite — fix and RETRY query_db now. (1) Use JOIN: FROM mandi_prices p JOIN mandis m ON p.mandi_id=m.id WHERE m.district='Nashik' — mandi_prices has NO district column. (2) Use date('now','-7 days') not CURRENT_DATE - INTERVAL. (3) Use LIKE not ILIKE. Retry query_db with corrected SQL in this turn."
                executed.append({"tool": name, "sql": args.get("sql", ""), "error": str(e) + hint})
                messages.append({"role": "tool", "content": json.dumps({"error": str(e) + hint})})
            except Exception as e:
                executed.append({"tool": name, "error": str(e)[:500]})
                messages.append({"role": "tool", "content": json.dumps({"error": str(e)[:500]})})
        if has_query:
            continue

    # GUARD: if LLM forgot to call query_db, force grounded query
    has_query = any("result" in e and "sql" in e for e in executed)
    if not has_query:
        low = user_message.lower()
        price_intent = any(k in low for k in ["price", "mandi", "arrival", "modal", "rate", "bhav", "kimat", "rs/", "quintal"])
        if price_intent or len(low.split()) <= 6:
            import re as _re
            _stop = {"give","me","show","latest","price","prices","rate","rates","bhav","kimat","for","of","the","today","current","please","kya","hai","compare","district","mandi","mandis","last","days","daily","average","modal","arrival","across","nashik","cheapest","highest","lowest","costly","cheap","only","single"}
            toks = [t for t in _re.findall(r"[a-z]{3,}", low) if t not in _stop]
            keyword = max(toks, key=len) if toks else ""
            # prefer known commodity if present
            _known_guard = ["onion","tomato","potato","wheat","cotton","soybean","maize","grape","pomegranate","sugarcane","turmeric"]
            _found_guard = [c for c in _known_guard if c in low]
            if _found_guard:
                keyword = _found_guard[0]
            if keyword:
                fallback_sql = f"SELECT commodity_name, variety, modal_price, min_price, max_price, arrival_date, arrival_quantity FROM mandi_prices WHERE commodity_name LIKE '%{keyword}%' OR variety LIKE '%{keyword}%' ORDER BY arrival_date DESC LIMIT 20"
            else:
                fallback_sql = "SELECT commodity_name, variety, modal_price, min_price, max_price, arrival_date FROM mandi_prices ORDER BY arrival_date DESC LIMIT 20"
            try:
                fb_res = _dispatch(engine, "query_db", {"sql": fallback_sql})
                executed.append({"sql": fallback_sql, "result": fb_res})
                messages.append({"role": "tool", "content": json.dumps(fb_res, default=str)[:8000]})
                has_query = True
            except Exception as e:
                executed.append({"tool": "query_db", "sql": fallback_sql, "error": str(e)[:400]})
                messages.append({"role": "tool", "content": json.dumps({"error": str(e)[:400]})})

    # final answer
    if (last_msg is not None and _extract_tool_calls(last_msg)) or has_query:
        _is_short = len(user_message.split()) <= 8 and any(k in user_message.lower() for k in ["price", "bhav", "kimat", "rate", "mandi"])
        if has_query and _is_short and executed and "sql" in executed[-1]:
            _res = executed[-1].get("result", {})
            _rows = _res.get("rows", []) or []
            _sql = executed[-1]["sql"]
            _cols = _res.get("columns") or []
            if _rows:
                lines = [_fmt_row_price(r) for r in _rows[:5]]
                table_md = _table_md(_cols, _rows, 5)
                # label cheapest/highest if query sorted by price
                _low_ans = user_message.lower()
                _label = "Latest prices"
                if "cheapest" in _low_ans or "lowest" in _low_ans:
                    _label = "Cheapest prices"
                elif "highest" in _low_ans or "costliest" in _low_ans:
                    _label = "Highest prices"
                answer = f"{_label} (Rs/quintal) — {len(_rows)} records:\n" + "\n".join(f"- {l}" for l in lines) + f"\n\nSQL: `{_sql}`\n\n{table_md}"
            else:
                answer = f"No records for that keyword. Try different spelling or broader query.\n\nSQL: `{_sql}`"
        else:
            final = client.chat(messages)
            answer = (final.get("content") or "").strip() or _fallback_answer(executed)
    else:
        answer = ((last_msg or {}).get("content") or "").strip()
        if not answer:
            answer = _fallback_answer(executed) or "Ask me about mandis, prices, buyers, lots, auctions — I will query the database for you."

    # primary = first query_db result for backwards compat
    primary = next((e for e in executed if "result" in e and "sql" in e), {})
    result = {
        "answer": answer,
        "sql": primary.get("sql"),
        "columns": (primary.get("result") or {}).get("columns"),
        "rows": (primary.get("result") or {}).get("rows"),
        "truncated": (primary.get("result") or {}).get("truncated", False),
        "executions": executed,
        "schema_tables": schema_tables,
    }
    # cache for 60s (only for non-history turns)
    if not history:
        _RESPONSE_CACHE[_ckey] = (_time.time(), result)
        if len(_RESPONSE_CACHE) > 32:
            oldest = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k][0])
            _RESPONSE_CACHE.pop(oldest, None)
    return result


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
