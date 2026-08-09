"""
Document ingestion.

    scan -> parse -> extract metadata -> chunk -> embed -> store

Runs as its own job, on its own schedule, and must never block the weekly sales
load. If a document fails, it is recorded and skipped; every other document
still loads.

    python -m aurelia.rag.ingest            # only what changed
    python -m aurelia.rag.ingest --force    # everything
"""
from __future__ import annotations
import os, re, json, hashlib, logging, argparse, datetime as dt
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import text

from aurelia import db

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

log = logging.getLogger(__name__)
_client: OpenAI | None = None

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIMS = 3072                      # full dimension; see schema.sql for why unindexed
META_MODEL = os.getenv("META_MODEL", "gpt-4o-mini")

DOCS = ROOT / "data" / "documents"
NEWS = ROOT / "data" / "news"


def _openai() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# ---------------------------------------------------------------- metadata
class DocMeta(BaseModel):
    """What the model is asked to pull out of a document."""
    doc_type: str = Field(description="campaign_plan | meeting_notes | ops_report")
    title: str
    doc_date: str = Field(description="when it was written, YYYY-MM-DD")
    period_start: str | None = Field(None, description="earliest week discussed, YYYY-Www")
    period_end: str | None = Field(None, description="latest week discussed, YYYY-Www")
    summary: str = Field(description="one sentence: what decision or fact this records")


META_PROMPT = """
Extract metadata from an internal retail document.

doc_type must be one of: campaign_plan, meeting_notes, ops_report.

doc_date is when the document was written. It is usually stated near the top.

period_start and period_end are the weeks the document TALKS ABOUT, which is
often different from when it was written. A June meeting can set August targets.
Use ISO weeks, YYYY-Www. If the document mentions dates but not weeks, convert
them. If it discusses no specific period, leave both null.

summary is one sentence naming the decision or fact the document records. Not a
description of the document type - the actual content.
""".strip()

SKU_RE = re.compile(r"\b[A-Z]{3}-[A-Z]{2}-[A-Z]{3}(?:-\d{2})?\b")


def _entities(textblob: str, products) -> dict:
    """
    SKUs and model names mentioned. Regex, not a model call - these are exact
    strings and a model would occasionally paraphrase them.
    """
    skus = sorted(set(SKU_RE.findall(textblob)) & set(products.sku))
    models = sorted({m for m in products.model.unique() if m.lower() in textblob.lower()})
    depts = sorted({d for d in products.department.unique() if d.lower() in textblob.lower()})
    if skus:  # a SKU implies its model and department
        sub = products[products.sku.isin(skus)]
        models = sorted(set(models) | set(sub.model))
        depts = sorted(set(depts) | set(sub.department))
    return dict(skus=skus, models=models, departments=depts)


def extract_meta(name: str, body: str) -> DocMeta:
    r = _openai().beta.chat.completions.parse(
        model=META_MODEL,
        messages=[{"role": "system", "content": META_PROMPT},
                  {"role": "user", "content": f"Filename: {name}\n\n{body[:6000]}"}],
        response_format=DocMeta)
    return r.choices[0].message.parsed


# ---------------------------------------------------------------- chunking
def chunk_markdown(body: str, max_chars: int = 1400) -> list[dict]:
    """
    Split on markdown headings rather than a fixed character count.

    These documents are meeting minutes and reports - one heading is one agenda
    item, one decision. A fixed-size split would cut a decision in half and merge
    two unrelated ones, which is the single biggest cause of a retrieved passage
    that reads as if it says something it does not.

    Each chunk keeps its heading, so a passage still says what it is about.
    """
    lines = body.split("\n")
    out, cur, head = [], [], ""
    for ln in lines:
        if re.match(r"^#{1,3}\s", ln):
            if cur and any(x.strip() for x in cur):
                out.append(dict(heading=head, content="\n".join(cur).strip()))
            head, cur = ln.lstrip("# ").strip(), [ln]
        else:
            cur.append(ln)
    if cur and any(x.strip() for x in cur):
        out.append(dict(heading=head, content="\n".join(cur).strip()))

    # split anything still oversized on blank lines, keeping the heading
    final = []
    for c in out:
        if len(c["content"]) <= max_chars:
            final.append(c); continue
        buf = ""
        for para in c["content"].split("\n\n"):
            if len(buf) + len(para) > max_chars and buf:
                final.append(dict(heading=c["heading"], content=buf.strip())); buf = ""
            buf += para + "\n\n"
        if buf.strip():
            final.append(dict(heading=c["heading"], content=buf.strip()))
    return [c for c in final if len(c["content"]) > 40]


# ---------------------------------------------------------------- embedding
def embed(texts: list[str]) -> list[list[float]]:
    """One batched call. Only ever runs for documents that actually changed."""
    if not texts:
        return []
    r = _openai().embeddings.create(model=EMBED_MODEL, input=texts, dimensions=EMBED_DIMS)
    return [d.embedding for d in r.data]


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


# ---------------------------------------------------------------- store
def _upsert(conn, doc: dict, chunks: list[dict], vectors: list[list[float]]):
    conn.execute(text("DELETE FROM documents WHERE doc_id = :d"), {"d": doc["doc_id"]})
    conn.execute(text("""
        INSERT INTO documents (doc_id, source_type, doc_type, title, doc_date,
                               period_start, period_end, entities, source_path,
                               content_hash, file_mtime, file_size)
        VALUES (:doc_id, :source_type, :doc_type, :title, :doc_date,
                :period_start, :period_end, CAST(:entities AS jsonb), :source_path,
                :content_hash, :file_mtime, :file_size)"""), doc)

    for i, (c, v) in enumerate(zip(chunks, vectors)):
        conn.execute(text("""
            INSERT INTO doc_chunks (chunk_id, doc_id, position, page, content, entities,
                                    doc_type, doc_date, period_start, period_end, embedding)
            VALUES (:chunk_id, :doc_id, :position, NULL, :content, CAST(:entities AS jsonb),
                    :doc_type, :doc_date, :period_start, :period_end, CAST(:emb AS vector))"""),
            dict(chunk_id=c["chunk_id"], doc_id=doc["doc_id"], position=i,
                 content=c["text"], entities=json.dumps(c["entities"]),
                 doc_type=doc["doc_type"], doc_date=doc["doc_date"],
                 period_start=doc["period_start"], period_end=doc["period_end"],
                 emb=_vec(v)))


def _unchanged(conn, path: Path, digest: str) -> bool:
    r = conn.execute(text("SELECT content_hash FROM documents WHERE source_path = :p"),
                     {"p": str(path)}).fetchone()
    return bool(r and r[0] == digest)


# ---------------------------------------------------------------- run
def run(force: bool = False) -> dict:
    d = db.load()
    products = d["products"]
    stats = dict(scanned=0, skipped=0, ingested=0, chunks=0, failed=[])
    eng = db.engine()

    files = sorted(DOCS.glob("*.md"))
    now = dt.datetime.now().timestamp()

    with eng.begin() as conn:
        for f in files:
            stats["scanned"] += 1
            st = f.stat()

            # still being written? leave it for the next run (unless --force)
            if not force and now - st.st_mtime < 60:
                stats["skipped"] += 1
                continue

            body = f.read_text()
            digest = hashlib.sha256(body.encode()).hexdigest()

            if not force and _unchanged(conn, f, digest):
                stats["skipped"] += 1
                continue

            try:
                meta = extract_meta(f.name, body)
                ents = _entities(body, products)
                chunks = chunk_markdown(body)
                for c in chunks:
                    c["text"] = (f"[{meta.title} — {c['heading']}]\n{c['content']}"
                                 if c["heading"] else c["content"])
                    c["entities"] = _entities(c["content"], products)
                    c["chunk_id"] = hashlib.sha256(
                        (str(f) + c["text"]).encode()).hexdigest()[:32]

                vectors = embed([c["text"] for c in chunks])

                _upsert(conn, dict(
                    doc_id=hashlib.sha256(str(f).encode()).hexdigest()[:32],
                    source_type="internal", doc_type=meta.doc_type, title=meta.title,
                    doc_date=meta.doc_date, period_start=meta.period_start,
                    period_end=meta.period_end, entities=json.dumps(ents),
                    source_path=str(f), content_hash=digest,
                    file_mtime=dt.datetime.fromtimestamp(st.st_mtime),
                    file_size=st.st_size), chunks, vectors)

                stats["ingested"] += 1
                stats["chunks"] += len(chunks)
                log.info("%s -> %s chunks", f.name, len(chunks))
            except Exception as e:
                stats["failed"].append(dict(file=f.name, error=f"{type(e).__name__}: {e}"))
                log.warning("failed %s: %s", f.name, e)

        # news arrives as one JSONL feed, one item per line
        feed = NEWS / "news_feed.jsonl"
        if feed.exists():
            items = [json.loads(l) for l in feed.read_text().splitlines() if l.strip()]
            texts, rows = [], []
            for n in items:
                blob = f"[{n['source']} — {n['title']}]\n{n['body']}"
                rows.append((n, blob))
                texts.append(blob)
            digest = hashlib.sha256(feed.read_bytes()).hexdigest()
            if force or not _unchanged(conn, feed, digest):
                vectors = embed(texts)
                for (n, blob), v in zip(rows, vectors):
                    did = hashlib.sha256(n["id"].encode()).hexdigest()[:32]
                    ents = dict(brands=n["entities"].get("brands", []),
                                categories=n["entities"].get("categories", []),
                                market=n["entities"].get("market", []),
                                skus=[], models=[], departments=[])
                    _upsert(conn, dict(
                        doc_id=did, source_type="external", doc_type="news",
                        title=n["title"], doc_date=n["date"],
                        period_start=None, period_end=None,
                        entities=json.dumps(ents), source_path=n["url"],
                        content_hash=digest, file_mtime=None, file_size=len(blob)),
                        [dict(chunk_id=did + "-0", text=blob, entities=ents)], [v])
                    stats["ingested"] += 1
                    stats["chunks"] += 1
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-ingest everything")
    a = ap.parse_args()
    print(json.dumps(run(force=a.force), indent=2))
