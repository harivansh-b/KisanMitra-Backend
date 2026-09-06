"""Lazy schema-discovery tools — LangChain SQLDatabaseToolkit-style.

No DDL dump upfront. LLM discovers lazily:
  list_tables() -> names
  get_table_info(table) -> columns + FK + indexes + pg_description + 3 sample rows
  query_db(sql) -> existing executor (SELECT/WITH only)
  explain_query(sql) -> EXPLAIN dry-run checker
"""
from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .schema import get_schema


def list_tables(engine) -> dict:
    schema = get_schema(engine)
    return {"tables": schema["table_names"], "count": len(schema["table_names"])}


def _pg_comment(conn, table: str) -> str | None:
    try:
        row = conn.execute(text(
            "SELECT obj_description(c.oid) FROM pg_class c "
            "WHERE c.relname = :t AND c.relkind IN ('r','p')"
        ), {"t": table}).fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def _col_comments(conn, table: str) -> dict[str, str]:
    try:
        rows = conn.execute(text(
            """
            SELECT a.attname, d.description
            FROM pg_description d
            JOIN pg_class c ON c.oid = d.objoid
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.objnum
            WHERE c.relname = :t AND d.objsubid > 0
            """
        ), {"t": table}).fetchall()
        return {r[0]: r[1] for r in rows if r[1]}
    except Exception:
        return {}


def get_table_info(engine, table: str) -> dict:
    from sqlalchemy import inspect
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return {"error": f"table '{table}' not found", "available": insp.get_table_names()}

    # columns + PK/FK/indexes via inspector
    cols = []
    for c in insp.get_columns(table):
        cols.append({
            "name": c["name"],
            "type": str(c["type"]),
            "nullable": bool(c.get("nullable")),
            "pk": bool(c.get("primary_key")),
            "default": str(c.get("default")) if c.get("default") is not None else None,
        })
    fks = []
    try:
        for fk in insp.get_foreign_keys(table):
            fks.append({
                "constrained": fk.get("constrained_columns"),
                "referred": f"{fk.get('referred_table')}.{fk.get('referred_columns')}",
                "options": fk.get("options", {}),
            })
    except Exception:
        pass
    indexes = []
    try:
        for ix in insp.get_indexes(table):
            indexes.append({"name": ix.get("name"), "columns": ix.get("column_names"), "unique": ix.get("unique")})
    except Exception:
        pass

    # comments + sample rows
    table_comment = None
    col_comments: dict[str, str] = {}
    sample_rows: list[dict] = []
    try:
        with engine.connect() as conn:
            table_comment = _pg_comment(conn, table)
            col_comments = _col_comments(conn, table)
            # sample rows — use quoted identifier; safe since table validated via inspector
            try:
                # naive quote for safety
                q = '"' + table.replace('"', '""') + '"'
                res = conn.execute(text(f"SELECT * FROM {q} LIMIT 3"))
                keys = list(res.keys())
                for r in res.fetchall():
                    d = dict(zip(keys, r))
                    for k, v in list(d.items()):
                        if hasattr(v, "isoformat"):
                            d[k] = v.isoformat()
                    sample_rows.append(d)
            except SQLAlchemyError:
                sample_rows = []
    except Exception:
        pass

    return {
        "table": table,
        "comment": table_comment,
        "columns": cols,
        "col_comments": col_comments,
        "fks": fks,
        "indexes": indexes,
        "sample_rows": sample_rows,
    }


def explain_query(engine, sql: str) -> dict:
    """Dry-run checker — EXPLAIN without executing. Returns {ok, plan} or {ok:false, error}."""
    from .executor import validate_sql
    try:
        sql = validate_sql(sql)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    try:
        with engine.connect() as conn:
            # EXPLAIN works on Postgres + SQLite (subset)
            res = conn.execute(text(f"EXPLAIN {sql}"))
            plan = [dict(zip(res.keys(), r)) for r in res.fetchall()][:20]
            return {"ok": True, "plan_rows": len(plan), "plan": plan}
    except SQLAlchemyError as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {str(e)[:500]}"}
