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
# naive ; chaining check — only one statement allowed
MULTI_STMT_RE = re.compile(r";\s*\S")


def validate_sql(sql: str) -> str:
    raw = sql.strip()
    # Check before tolerating one optional trailing semicolon. Otherwise a
    # chained mutation can be obscured by rstrip(";")/normalization.
    if MULTI_STMT_RE.search(raw):
        raise ValueError("multiple statements not allowed (single SELECT only)")
    s = raw.rstrip(";").strip()
    if not s:
        raise ValueError("empty sql")
    # must start with SELECT or WITH
    if not re.match(r"^\s*(SELECT|WITH)\b", s, re.IGNORECASE):
        raise ValueError("only SELECT / WITH ... SELECT allowed")
    if FORBIDDEN_RE.search(s):
        raise ValueError("mutation/DDL keywords not allowed")
    return s


def run_query(engine, sql: str, params: dict | None = None, limit: int = 100, timeout_ms: int = 5000) -> dict:
    """Execute validated SELECT and return {columns, rows, rowcount}."""
    sql = validate_sql(sql)
    # enforce limit if missing — wrap politely, don't rewrite complex SQL; just append via driver if needed
    # we enforce via fetch cap instead of rewriting
    params = params or {}
    # set statement timeout on Postgres; no-op on SQLite
    try:
        with engine.connect() as conn:
            try:
                conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
            except Exception:
                pass  # SQLite / non-postgres
            result = conn.execute(text(sql), params)
            cols = list(result.keys())
            rows_raw = result.fetchmany(limit)
            rows = [dict(zip(cols, r)) for r in rows_raw]
            # stringify non-json types
            for r in rows:
                for k, v in list(r.items()):
                    if hasattr(v, "isoformat"):
                        r[k] = v.isoformat()
            return {"columns": cols, "rows": rows, "rowcount": len(rows), "truncated": result.fetchone() is not None}
    except SQLAlchemyError as e:
        # sanitized error — no internal table exposure beyond message
        raise ValueError(f"query failed: {e.__class__.__name__}: {str(e)[:400]}") from e
