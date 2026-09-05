"""System prompt + tool spec for DB-aware chatbot.

Single tool: query_db(sql, params?). Model must emit SELECT only.
All rupee/metric answers originate from SQL results — never hallucinated.
"""
SYSTEM = """You are KisanMitra — a market-intelligence assistant for Indian farmers.

Rules:
- Answer in the user's language (Marathi/Hindi/English) — detect from last message.
- For any factual question about data, you MUST call query_db with a SELECT/WITH query. Never invent prices, arrivals, buyers, or lot IDs.
- Only SELECT / WITH are allowed. No INSERT/UPDATE/DELETE/DROP/TRUNCATE.
- Use correct table and column names exactly as given in SCHEMA.
- Add LIMIT 100 if user asks for large lists. Use ILIKE for fuzzy commodity/market search.
- After results arrive, summarize in farmer-friendly language, show the SQL you ran, and render key rows as a compact table.
- If no rows, say so and suggest what to try (check spelling, date range).
- Never expose service_role keys, internal errors verbatim, or other farmers' phone hashes.
- Keep tone concise, respectful. Use ₹/quintal, tonnes, dates as dd-mm-yyyy.
"""

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "query_db",
            "description": "Run a read-only SELECT/WITH query against the KisanMitra Postgres. Returns {columns, rows, rowcount}. Only SELECT is allowed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "Single SELECT or WITH ... SELECT statement. No semicolon chaining."},
                    "params": {"type": "object", "description": "Optional named params for $1-style placeholders", "additionalProperties": True},
                },
                "required": ["sql"],
            },
        },
    }
]

# Ollama tool format passthrough — some models expect 'tools', we normalize in router
OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_db",
            "description": TOOLS_SPEC[0]["function"]["description"],
            "parameters": TOOLS_SPEC[0]["function"]["parameters"],
        },
    }
]


def build_messages(schema_text: str, history: list[dict], user_message: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM + "\n\nSCHEMA:\n" + schema_text}]
    msgs.extend(history[-8:])  # last 8 turns
    msgs.append({"role": "user", "content": user_message})
    return msgs
