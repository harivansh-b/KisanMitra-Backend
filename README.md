# KisanMitra-Backend

**SIH 2026 — SIH26132** | Strengthening market linkages and price discovery for farmers  
*Govt. of Maharashtra — Maharashtra State Innovation Society*

Market-intelligence + transaction enablement platform: mandi prices, buyer demand, lot creation, price forecasting, and a DB-aware chatbot that answers any question by querying the live database.

> **Active branch:** `feat/chatbot-sql-agent` (commit `c3cc137`) — DB-aware SQL agent shipped, tests passing locally (FakeTransport + SQLite, no Ollama required).

---

## What is KisanMitra?

Farmers (especially smallholders/FPOs) lack visibility into mandi prices, buyer demand, quality specs, logistics, storage and payment reliability across nearby markets. Buyers struggle to aggregate consistent volume/quality.

KisanMitra aggregates mandi prices, buyer demand, arrival volumes, transport/storage options; provides localized price trends + sale-window recommendations; matches farmer/FPOs with verified buyers; enables lot creation, quality grading, digital offers, logistics coordination, payment tracking and grievance handling.

**This repo = backend.** Frontend + price-prediction service live in sibling dirs/services.

---

## Repo Map (actual, as shipped)

```
KisanMitra-Backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI entry — uvicorn app.main:app --reload
│   ├── config.py             # Settings (DATABASE_URL, SUPABASE_*, ASSISTANT_MODEL, OLLAMA_HOST, BHASHINI_*)
│   ├── db.py                 # Engine/Session — Supabase direct :5432, SQLite dev fallback
│   └── services/
│       ├── __init__.py
│       ├── chatbot/           # ← YOUR SCOPE — DB-aware SQL agent
│       │   ├── __init__.py    # re-exports OllamaClient, chat_once, router
│       │   ├── client.py      # OllamaClient — stdlib urllib only, FakeTransport for tests
│       │   ├── schema.py      # Live introspection via sqlalchemy.inspect — 5 min cache
│       │   ├── prompt.py      # SYSTEM + query_db tool spec (Marathi/Hindi/English)
│       │   ├── executor.py    # SELECT/WITH-only guard, 5s timeout, 100-row cap
│       │   ├── agent.py       # 2-turn loop: schema→LLM→query_db→run_query→grounded answer
│       │   ├── router.py      # POST /api/v1/chat, GET /api/v1/chat/schema, GET /health
│       │   └── rag.py         # Optional pgvector HNSW fallback (multilingual-e5-small 384d)
│       └── price_prediction/
│           └── __init__.py    # stub — teammate/you wire forecast model here
├── tests/
│   ├── __init__.py
│   └── test_chatbot.py       # 5 tests — no Ollama needed
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Tech Stack (as planned — locked for SIH2026)

| Layer | Choice | Why (SIH2026 judges) |
|-------|--------|----------------------|
| **API** | FastAPI 0.115 + Uvicorn 0.30 | async, OpenAPI, Pydantic validation |
| **DB** | Supabase Postgres direct `db.*.supabase.co:5432` + SQLAlchemy 2.0 + psycopg 3.1 | Supabase is **source of truth**; `DATABASE_URL=sqlite://` only for dev/tests |
| **Auth/Storage/Realtime** | Supabase (policies.sql enables `pgvector`, `postgis`, `pg_trgm`) | row-level security, lot photo buckets, live auction bids |
| **LLM** | **Local-first** — Ollama `qwen3:8b` default, swappable via `ASSISTANT_MODEL` → `sarvam-2b` / `bharatgenai/AgriParam` GGUF | Offline demo, ₹0 inference, Atmanirbhar — SIH2026 prioritizes local over paid APIs |
| **Chat transport** | `OllamaClient` (stdlib `urllib`, no pip dep) + `FakeTransport` in tests | import-safe without Ollama running |
| **Vector / RAG** | Supabase `pgvector` (already `create extension if not exists vector` in `supabase/policies.sql`) — `vector(384)` HNSW | single DB for RAG + transactional data; `fastembed` or `sentence-transformers` for `intfloat/multilingual-e5-small` |
| **Embedding** | `intfloat/multilingual-e5-small` (384d) or `BAAI/bge-m3` (1024d) | Marathi+Hindi+English single model |
| **Validation** | `sqlparse` + regex guard | read-only safety |
| **i18n/voice (planned)** | Bhashini (`BHASHINI_USER_ID/KEY` in config), Whisper/Coqui local | Marathi-first for Maharashtra org |

---

## Chatbot — DB-Aware SQL Agent (shipped)

Instead of hard-coded intents, the chatbot **reads the live DB schema** and writes SQL for any question.

```
User (mr/hi/en)
  → POST /api/v1/chat {message, history}
    → schema.py  — inspect(engine) → {tables, columns, fks} (cached 5 min)
    → prompt.py  — SYSTEM + SCHEMA + history → messages[]
    → Ollama qwen3:8b (or Sarvam/AgriParam) → tool call query_db{sql}
    → executor.py — validate (SELECT/WITH only, no ; chaining, no DDL) → run_query()
    → agent responds with {answer, sql, columns, rows, truncated}
```

**Guarantees:**
- **Read-only** — only `SELECT`/`WITH ... SELECT`; blocks `INSERT/UPDATE/DELETE/DROP/TRUNCATE/ALTER/CREATE`.
- **Single statement** — rejects `; DROP` chaining.
- **No hallucination** — every rupee/arrival/buyer figure comes from a SQL result, never LLM memory.
- **Auto-adapts** — teammate pushes a new table → `get_schema(force=True)` picks it up, zero code change.
- **Auditable** — response includes the SQL that was run + a row table (demo wow-factor).

**pgvector RAG (`rag.py`)** — optional semantic fallback when SQL returns 0 rows. DDL (run once in Supabase SQL editor after `alembic upgrade head`):

```sql
create extension if not exists vector;
create table if not exists rag_docs (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  metadata jsonb default '{}',
  embedding vector(384)
);
create index if not exists rag_docs_hnsw on rag_docs using hnsw (embedding vector_cosine_ops);
alter table rag_docs enable row level security;
create policy "open read rag" on rag_docs for select using (true);
```

Embed with `fastembed` (`TextEmbedding("intfloat/multilingual-e5-small")`) or `sentence-transformers`.

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | `{status, service, version}` |
| `POST` | `/api/v1/chat` | DB-aware Q&A — body `{message, history?, language?}` → `{answer, sql, columns, rows, truncated, schema_tables}` |
| `GET` | `/api/v1/chat/schema` | Live schema dump (forced refresh) — `{tables, table_names}` |
| `GET` | `/api/v1/chat/health` | Chatbot sub-health |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"onion price in Pune last week? top 5"}'
# → {"answer":"Top onion: Nashik 1700, Pune 1500 ...","sql":"SELECT ...","rows":[...]}
```

Marathi:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"कांद्याचा भाव काय आहे पुण्यात?"}'
```

---

## Local Setup & Test

```bash
# 1. Clone (chatbot branch)
git clone https://github.com/harivansh-b/KisanMitra-Backend.git
cd KisanMitra-Backend
git checkout feat/chatbot-sql-agent

# 2. Env
cp .env.example .env
# edit DATABASE_URL — Supabase direct when ready, else sqlite for dev:
# DATABASE_URL=sqlite:///./kisanmitra.db
# DATABASE_URL=postgresql+psycopg://postgres.PROJECT:PASS@db.PROJECT.supabase.co:5432/postgres
# ASSISTANT_MODEL=qwen3:8b          # or sarvam-2b / AgriParam GGUF via Ollama
# OLLAMA_HOST=http://localhost:11434

# 3. Install
pip install -r requirements.txt
# optional RAG embedding offline:
# pip install fastembed

# 4. Run (no DB migration needed — SQLite auto-creates; Supabase uses Alembic when teammate pushes it)
uvicorn app.main:app --reload
# → http://localhost:8000/health
# → http://localhost:8000/docs  (Swagger)

# 5. With real LLM (local, no API bill)
ollama serve &
ollama pull qwen3:8b
curl -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" \
  -d '{"message":"list markets"}'

# 6. Tests (no Ollama needed — FakeTransport + in-memory SQLite)
pytest -q
# or without pytest:
python -c "from tests.test_chatbot import *; print('import ok')"
```

**What was verified locally (EXIT:0, no Ollama):**
- Schema introspection discovers 6 tables, FK hints, 6k-char truncation
- Executor allows `SELECT`/`WITH`, blocks `DELETE`/`DROP`/multi-stmt, enforces 100-row cap + `truncated` flag
- `AVG(modal_price) GROUP BY`, window functions, `ILIKE` via `LIKE COLLATE NOCASE` all pass
- Agent 2-turn loop: `tools→query_db→execute→grounded answer`; greeting no-tool path; bad-SQL error caught gracefully
- RAG `_has_rag` false when no `rag_docs` table — silent no-op
- Marathi query → SQL + Marathi answer
- Full FastAPI e2e via `TestClient` with file DB → `200 {answer, sql, rows}`

---

## Environment Variables

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `sqlite:///./kisanmitra.db` | Supabase direct `postgresql+psycopg://...@db.*.supabase.co:5432/postgres` in prod |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` | `""` | Supabase dashboard |
| `ASSISTANT_MODEL` | `qwen3:8b` | `sarvam-2b`, `bharatgenai/AgriParam` GGUF — same `OllamaClient` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama `/api/chat` |
| `BHASHINI_USER_ID` / `BHASHINI_API_KEY` | `""` | Bhashini translation (planned) |

---

## Git

- **Default branch:** `main` (1 commit `e2914af Initial commit` — 2 stubs)
- **Active work:** `feat/chatbot-sql-agent` → `c3cc137 feat(chatbot): DB-aware SQL agent + pgvector RAG` — 17 files, 645 insertions
- **PR:** https://github.com/harivansh-b/KisanMitra-Backend/pull/new/feat/chatbot-sql-agent
- **Push:** `git push -u origin feat/chatbot-sql-agent` done.

---

## What Done vs What Next

**Done:**
- [x] Repo mapped (was 3-file skeleton)
- [x] Stack locked with Supabase + local LLM rationale for SIH2026 judging (local/cheap/offline/Atmanirbhar)
- [x] `pgvector` confirmed available on Supabase (`policies.sql:8` already enabled)
- [x] Chatbot scaffold — 7 modules (client, schema, prompt, executor, agent, router, rag) + shared config/db
- [x] FastAPI wired (`app/main.py`), `requirements.txt`, `.env.example`, `.gitignore`
- [x] Tests (`FakeTransport` + SQLite mem) + local e2e via `TestClient` all passing
- [x] Branch pushed, no secrets, no API bill

**Next (your call):**
- [ ] Teammate pushes Supabase tables / Alembic — chatbot needs zero change (auto-discovers)
- [ ] Price-prediction service (`app/services/price_prediction`) → expose as `forecast_price(crop, mandi)` tool if needed
- [ ] Wire Bhashini/Marathi STT for voice + `fastembed` population of `rag_docs`
- [ ] Add `auth` dependency (Supabase JWT → `farmer_id` filter injection) before prod
- [ ] Deploy: Docker + `uvicorn` + Supabase; demo offline via Ollama Q4 quantized model

---

## SIH2026 Notes

- **Evaluation:** Novelty 20% / Feasibility 25% / Impact 25% / UX 15% / Implementation 15%. Local + offline + zero cost scores high on Feasibility & Impact.
- **Why local > API:** cost at farmer scale, 2G/offline rural, data sovereignty, reproducible judging (no API key to expire). Show airplane-mode demo.
- **Language:** Maharashtra org → Marathi native is not optional. `Sarvam-2b` or `AgriParam + IndicTrans2/Bhashini` bridge required; current `qwen3:8b` is placeholder swappable via env.

---

## License

Internal — SIH 2026 submission. Not for redistribution until finale.
