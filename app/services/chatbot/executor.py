"""Read-only SQL executor — whitelist SELECT/WITH, block mutation, timeout + row cap.

Server-side safety for a DB-aware agent that writes SQL on behalf of users.
"""
from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|VACUUM|COPY|CALL)\b",
    re.IGNORECASE,
)
MULTI_STMT_RE = re.compile(r";\s*\S")


def validate_sql(sql: str) -> str:
    raw = sql.strip()
    if MULTI_STMT_RE.search(raw):
        raise ValueError("multiple statements not allowed (single SELECT only)")
    s = raw.rstrip(";").strip()
    if not s:
        raise ValueError("empty sql")
    if not re.match(r"^\s*(SELECT|WITH)\b", s, re.IGNORECASE):
        raise ValueError("only SELECT / WITH ... SELECT allowed")
    if FORBIDDEN_RE.search(s):
        raise ValueError("mutation/DDL keywords not allowed")
    return s


def _sqlite_compat(sql: str, engine) -> str:
    """Translate common Postgresisms to SQLite so naive LLM SQL still runs."""
    # auto-fix: mandi_prices has NO district column — inject JOIN mandis if filter uses district without join
    # Must run regardless of dialect (also helps Postgres if model forgets JOIN, but Postgres will error with hint anyway)
    if re.search(r"\bFROM\s+mandi_prices\b", sql, re.IGNORECASE) and re.search(r"\bdistrict\b", sql, re.IGNORECASE) and "mandis" not in sql.lower():
        sql = re.sub(r"\bFROM\s+mandi_prices\b", "FROM mandi_prices p JOIN mandis m ON p.mandi_id=m.id", sql, flags=re.IGNORECASE, count=1)
        if "m.district" not in sql.lower():
            sql = re.sub(r"(?<!\.)\bdistrict\b", "m.district", sql, flags=re.IGNORECASE)
        sql = sql.replace("m.m.district", "m.district").replace("m.M.district", "m.district")
        # fix WHERE p.district duplicate if we aliased — ensure WHERE m.district
        sql = re.sub(r"\bp\.district\b", "m.district", sql, flags=re.IGNORECASE)

    if getattr(getattr(engine, "dialect", None), "name", "") != "sqlite":
        # still normalize ILIKE for Postgres? No — Postgres supports ILIKE, keep it
        return sql

    # Postgres date syntax -> SQLite
    sql = re.sub(
        r"CURRENT_DATE\s*-\s*INTERVAL\s*'(\d+)\s*(day|days|month|months|year|years|hour|hours|minute|minutes)'",
        lambda m: f"date('now','-{m.group(1)} {m.group(2)}')",
        sql, flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"NOW\(\)\s*-\s*INTERVAL\s*'(\d+)\s*(day|days|month|months|year|years|hour|hours)'",
        lambda m: f"datetime('now','-{m.group(1)} {m.group(2)}')",
        sql, flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"DATE_SUB\s*\(\s*(CURRENT_DATE|NOW\(\)|date\('now'\))\s*,\s*INTERVAL\s*(\d+)\s*(DAY|DAYS|MONTH|MONTHS|YEAR|YEARS|HOUR|HOURS)\s*\)",
        lambda m: f"date('now','-{m.group(2)} {m.group(3).lower()}')",
        sql, flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"INTERVAL\s*'(\d+)\s*(day|days|month|months|year|years|hour|hours)'",
        lambda m: f"'-{m.group(1)} {m.group(2)}'",
        sql, flags=re.IGNORECASE,
    )
    sql = re.sub(r"\bCURRENT_DATE\b", "date('now')", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bNOW\(\)", "datetime('now')", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bILIKE\b", "LIKE", sql, flags=re.IGNORECASE)
    return sql


def run_query(engine, sql: str, params: dict | None = None, limit: int = 100, timeout_ms: int = 5000) -> dict:
    """Execute validated SELECT and return {columns, rows, rowcount}."""
    sql = _sqlite_compat(sql, engine)
    sql = validate_sql(sql)
    params = params or {}
    try:
        with engine.connect() as conn:
            try:
                conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
            except Exception:
                pass
            result = conn.execute(text(sql), params)
            cols = list(result.keys())
            rows_raw = result.fetchmany(limit)
            rows = [dict(zip(cols, r)) for r in rows_raw]
            for r in rows:
                for k, v in list(r.items()):
                    if hasattr(v, "isoformat"):
                        r[k] = v.isoformat()
            return {"columns": cols, "rows": rows, "rowcount": len(rows), "truncated": result.fetchone() is not None}
    except SQLAlchemyError as e:
        raise ValueError(f"query failed: {e.__class__.__name__}: {str(e)[:400]}") from e
