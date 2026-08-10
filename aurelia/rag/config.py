"""Shared RAG settings. Keep in sync with db/schema.sql vector(3072)."""

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIMS = 3072  # full dimension; see schema.sql for why unindexed
