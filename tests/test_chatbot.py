"""Chatbot db-aware tests — no Ollama needed (FakeTransport) + in-memory SQLite."""
import json
from sqlalchemy import create_engine, text

from app.services.chatbot.agent import chat_once
from app.services.chatbot.client import OllamaClient
from app.services.chatbot.executor import validate_sql, run_query
from app.services.chatbot.schema import get_schema


def _mem_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    eng.execute = eng.connect  # compat
    with eng.begin() as conn:
        conn.execute(text("create table markets (id integer primary key, name text, district text)"))
        conn.execute(text("create table mandi_prices (id integer primary key, market_id integer, commodity text, modal_price real, arrival_date text)"))
        conn.execute(text("insert into markets values (1,'Pune APMC','Pune'),(2,'Nashik','Nashik')"))
        conn.execute(text("insert into mandi_prices values (1,1,'Onion',1500,'2026-09-01'),(2,2,'Onion',1700,'2026-09-01')"))
    return eng


def test_validate_allows_select():
    assert validate_sql("SELECT * FROM markets") == "SELECT * FROM markets"


def test_validate_blocks_mutation():
    try:
        validate_sql("DELETE FROM markets")
        assert False, "should block"
    except ValueError as e:
        assert "only SELECT" in str(e)


def test_validate_blocks_multi_stmt():
    try:
        validate_sql("SELECT 1; DROP TABLE markets")
        assert False
    except ValueError as e:
        assert "multiple" in str(e).lower()


def test_run_query_sqlite():
    eng = _mem_engine()
    res = run_query(eng, "select name from markets order by id")
    assert res["columns"] == ["name"]
    assert len(res["rows"]) == 2


def test_schema_discovers_tables():
    eng = _mem_engine()
    s = get_schema(eng, force=True)
    assert "markets" in s["table_names"]
    assert "mandi_prices" in s["table_names"]


def test_chat_once_fake_transport():
    eng = _mem_engine()

    def fake(messages, tools):
        # first call has tools -> emit query_db, second call no tools -> answer
        if tools:
            return {
                "tool_calls": [{"function": {"name": "query_db", "arguments": json.dumps({"sql": "select name, modal_price from mandi_prices join markets on markets.id=mandi_prices.market_id where commodity='Onion'"})}}],
                "content": "",
            }
        return {"content": "Found 2 onion prices: Pune 1500, Nashik 1700", "tool_calls": []}

    client = OllamaClient(transport=fake)
    res = chat_once(eng, client, "onion price in maharashtra?")
    assert "1500" in res["answer"] or res["rows"] is not None
    assert res["sql"] is not None
