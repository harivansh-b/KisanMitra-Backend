"""Live DB schema introspection — auto-discovers teammate tables.

No hard-coded table list. Cached 5 min. Works on Postgres (Supabase)
and SQLite (dev). Output is compact JSON injected into LLM prompt.
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import inspect

_CACHE: dict[str, Any] = {"ts": 0, "schema": None}
TTL_S = 300


def get_schema(engine, force: bool = False) -> dict:
    """Return {tables: [{name, columns: [{name,type,nullable,pk}], fks, indexes}]}."""
    now = time.time()
    if not force and _CACHE["schema"] is not None and (now - _CACHE["ts"]) < TTL_S:
        return _CACHE["schema"]

    insp = inspect(engine)
    tables = []
    for tname in insp.get_table_names():
        # skip alembic bookkeeping
        if tname in ("alembic_version", "spatial_ref_sys"):
            continue
        cols = []
        for c in insp.get_columns(tname):
            cols.append({
                "name": c["name"],
                "type": str(c["type"]),
                "nullable": bool(c.get("nullable")),
                "pk": bool(c.get("primary_key")),
            })
        # foreign keys for join hints
        fks = []
        try:
            for fk in insp.get_foreign_keys(tname):
                fks.append({"constrained": fk.get("constrained_columns"), "referred": f"{fk.get('referred_table')}.{fk.get('referred_columns')}"})
        except Exception:
            pass
        tables.append({"name": tname, "columns": cols, "fks": fks})

    schema = {"tables": tables, "table_names": [t["name"] for t in tables]}
    _CACHE.update(ts=now, schema=schema)
    return schema


def schema_text(schema: dict, max_chars: int = 6000) -> str:
    """Compact DDL-like text for prompt — truncated to token budget."""
    lines: list[str] = []
    for t in schema["tables"]:
        col_str = ", ".join(f"{c['name']} {c['type']}" + (" PK" if c["pk"] else "") for c in t["columns"])
        lines.append(f"TABLE {t['name']} ({col_str})")
        for fk in t.get("fks", []):
            lines.append(f"  FK {fk['constrained']} -> {fk['referred']}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n-- (truncated, ask for specific table) --"
    return text
