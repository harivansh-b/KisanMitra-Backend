"""System prompt + tool spec for DB-aware chatbot.

Single tool: query_db(sql, params?). Model must emit SELECT only.
All rupee/metric answers originate from SQL results — never hallucinated.
"""
SYSTEM = """You are KisanMitra — a market-intelligence assistant for Indian farmers.

Rules:
- Answer in the user's language (Marathi/Hindi/English) — detect from last message.
- For factual data, discover schema LAZILY via tools — do NOT guess table/column names.
  Flow: list_tables → get_table_info(relevant tables) → explain_query(optional) → query_db.
- You MUST call query_db with SELECT/WITH for any price/arrival/buyer/lot answer. Never invent.
- Only SELECT / WITH allowed. No INSERT/UPDATE/DELETE/DDL.
- Use exact column names from get_table_info. Add LIMIT 100 for lists, ILIKE for fuzzy.
- After rows arrive, summarize farmer-friendly, show SQL, render compact table.
- If no rows, say so and suggest fix (spelling, date range, other table).
- Never expose keys, hashes, or internal errors verbatim. ₹/quintal, tonnes, dd-mm-yyyy.
"""

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List all marketplace tables. Call first to discover where data lives. Returns {tables, count}.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_info",
            "description": "Get columns, PK/FK, indexes, pg_description comments, and 3 sample rows for one table. Call for 1-3 relevant tables after list_tables.",
            "parameters": {
                "type": "object",
                "properties": {"table": {"type": "string", "description": "Exact table name from list_tables"}},
                "required": ["table"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_query",
            "description": "Dry-run EXPLAIN for a SELECT/WITH. Validates SQL without executing. Returns {ok, plan} or {ok:false, error}.",
            "parameters": {
                "type": "object",
                "properties": {"sql": {"type": "string", "description": "Single SELECT or WITH ... SELECT"}},
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_db",
            "description": "Run read-only SELECT/WITH. Returns {columns, rows, rowcount, truncated}. Only SELECT allowed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "Single SELECT or WITH ... SELECT. No semicolon chaining."},
                    "params": {"type": "object", "description": "Optional named params", "additionalProperties": True},
                },
                "required": ["sql"],
            },
        },
    },
]

# Ollama passthrough
OLLAMA_TOOLS = TOOLS_SPEC


def build_messages(schema_text: str, history: list[dict], user_message: str) -> list[dict]:
    # schema_text now is minimal hint — full DDL fetched lazily via get_table_info
    hint = schema_text if schema_text else "Call list_tables to discover available tables."
    msgs = [{"role": "system", "content": SYSTEM + "\n\nHINT:\n" + hint}]
    msgs.extend(history[-8:])
    msgs.append({"role": "user", "content": user_message})
    return msgs


def build_messages_lazy(history: list[dict], user_message: str, table_hint: str = "") -> list[dict]:
    hint = table_hint or "Call list_tables to discover tables."
    msgs = [{"role": "system", "content": SYSTEM + "\n\nHINT:\n" + hint}]
    msgs.extend(history[-8:])
    msgs.append({"role": "user", "content": user_message})
    return msgs
