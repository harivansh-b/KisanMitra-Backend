"""pgvector retriever — optional semantic fallback when SQL returns empty.

Requires Supabase Postgres with `create extension if not exists vector;`
and a `rag_docs` table. No-op if table/extension absent — chatbot still works SQL-only.

Table DDL (run once after alembic head in Supabase SQL editor):

    create extension if not exists vector;
    create table if not exists rag_docs (
      id uuid primary key default gen_random_uuid(),
      content text not null,
      metadata jsonb default '{}',
      embedding vector(384)
    );
    create index if not exists rag_docs_hnsw on rag_docs
      using hnsw (embedding vector_cosine_ops);
    -- optional RLS
    alter table rag_docs enable row level security;
    create policy "open read rag" on rag_docs for select using (true);

Embed with intfloat/multilingual-e5-small (384d, Marathi/Hindi/English)
or BAAI/bge-m3 (1024d) — set EMBEDDING_DIM accordingly.
"""
from __future__ import annotations

from sqlalchemy import text

EMBEDDING_DIM = 384  # e5-small; switch to 1024 for bge-m3


def _has_rag(engine) -> bool:
    """Probe rag_docs exists — cheap, cached by caller if needed."""
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1 from rag_docs limit 0"))
        return True
    except Exception:
        return False


def retrieve(engine, query_embedding: list[float], k: int = 5) -> list[dict]:
    """Cosine search via pgvector <=> . query_embedding must match EMBEDDING_DIM.

    Returns [{content, metadata, distance}]. Empty if table missing.
    """
    if len(query_embedding) != EMBEDDING_DIM:
        raise ValueError(f"embedding dim mismatch: got {len(query_embedding)}, expected {EMBEDDING_DIM}")
    if not _has_rag(engine):
        return []
    # param binding: pgvector expects '[0.1,0.2,...]'::vector literal or vector param
    vec_literal = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
    sql = text("""
        select content, metadata, embedding <=> (:vec)::vector as distance
        from rag_docs
        order by embedding <=> (:vec)::vector
        limit :k
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"vec": vec_literal, "k": k}).mappings().all()
    return [dict(r) for r in rows]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Lazy embed helper — tries fastembed, then sentence-transformers, else raises.

    Call offline to populate rag_docs. Not used in request path.
    """
    try:
        from fastembed import TextEmbedding  # type: ignore

        model = TextEmbedding("intfloat/multilingual-e5-small")
        return [list(v) for v in model.embed(texts)]
    except ImportError:
        pass
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model = SentenceTransformer("intfloat/multilingual-e5-small")
        return model.encode(texts, normalize_embeddings=True).tolist()
    except ImportError as e:
        raise ImportError(
            "install fastembed or sentence-transformers to embed: pip install fastembed"
        ) from e
