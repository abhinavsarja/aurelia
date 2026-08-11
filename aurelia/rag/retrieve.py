"""
Retrieval.

Filter first, then rank. That order is the whole design.

Meeting notes are highly self-similar - every buying committee discusses reorders,
budgets and ranges in nearly identical language. Across dozens of them a query
about a deferred reorder matches most equally well, because they genuinely are
all the same kind of document. A better embedding model does not fix that.

So three filters run before any similarity is computed:

    1. time window     - only documents whose period overlaps the weeks asked about
    2. product         - only chunks mentioning that SKU, model or department
    3. document type   - chosen by what the numbers already showed

After those, we are usually ranking tens of chunks rather than thousands, and
similarity is doing a small, easy job. That is what it is good at.
"""
from __future__ import annotations
import os, json, logging, datetime as dt
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import text

from aurelia import db
from aurelia.rag.config import EMBED_DIMS, EMBED_MODEL

load_dotenv()
log = logging.getLogger(__name__)
client = OpenAI(timeout=90.0, max_retries=2)

# What kind of document can explain what kind of finding. Free to apply, and it
# removes more noise than any tuning of the similarity threshold.
FINDING_TO_DOCTYPE = {
    "B1":       ["meeting_notes", "ops_report"],     # out of stock -> who decided, or who was late
    "C1/C2":    ["campaign_plan", "meeting_notes"],  # price moved  -> who priced it
    "RESIDUAL": ["campaign_plan", "meeting_notes", "ops_report"],
}


def _vec(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def _embed_query(q: str):
    r = client.embeddings.create(model=EMBED_MODEL, input=[q], dimensions=EMBED_DIMS)
    return r.data[0].embedding


def build_query(sku: str, findings: list[dict], products) -> str:
    """
    The search text is built from the FINDINGS, not from the user's question.

    Searching "why did sales drop" returns documents about sales dropping -
    semantically perfect, analytically useless. Searching "Marlow Crossbody Tan
    replenishment stock" returns the meeting where it was decided.
    """
    row = products[products.sku == sku]
    parts = [sku]
    if not row.empty:
        parts += [row.iloc[0].model, row.iloc[0].department, str(row.iloc[0].colour or "")]
    for f in findings:
        if f["id"] == "B1":
            parts += ["replenishment", "reorder", "stock", "out of stock", "delivery"]
        elif f["id"].startswith("C"):
            parts += ["price", "discount", "markdown", "campaign"]
        else:
            parts += ["campaign", "support", "demand", "range"]
    return " ".join(dict.fromkeys(p for p in parts if p))


def search(query: str, weeks: list[str] = None, skus: list[str] = None,
           models: list[str] = None, departments: list[str] = None,
           doc_types: list[str] = None, source_type: str = "internal",
           month: str = None, limit: int = 6) -> list[dict]:
    """Filtered similarity search. Returns chunks with everything needed to cite them."""
    where, params = ["d.source_type = :st"], {"st": source_type}

    # 1. time window
    # Calendar month (YYYY-MM) matches documents *dated* in that month - right for
    # "what was decided in the July meeting". Trading-week overlap is for gap
    # diagnosis, where the question is about performance in those weeks.
    if month:
        where.append("c.doc_date IS NOT NULL AND to_char(c.doc_date, 'YYYY-MM') = :month")
        params["month"] = month
    elif weeks:
        where.append("(c.period_start IS NULL OR c.period_start <= :wmax)")
        where.append("(c.period_end   IS NULL OR c.period_end   >= :wmin)")
        params |= {"wmin": min(weeks), "wmax": max(weeks)}

    # 2. product - chunk-level first, document-level as the fallback
    ent = []
    if skus:        ent.append("c.entities->'skus'  ?| :skus")
    if models:      ent.append("c.entities->'models' ?| :models")
    if departments: ent.append("c.entities->'departments' ?| :depts")
    if ent:
        where.append("(" + " OR ".join(ent) + " OR d.entities->'skus' ?| :skus)")
        params |= {"skus": skus or [], "models": models or [], "depts": departments or []}

    # 3. document type
    if doc_types:
        where.append("c.doc_type = ANY(:dt)")
        params["dt"] = doc_types

    params["q"] = _vec(_embed_query(query))
    params["lim"] = limit

    sql = f"""
        SELECT c.chunk_id, c.content, c.doc_type, c.doc_date,
               d.title, d.source_path, c.position,
               c.embedding <=> CAST(:q AS vector) AS distance
        FROM doc_chunks c JOIN documents d USING (doc_id)
        WHERE {' AND '.join(where)}
        ORDER BY distance
        LIMIT :lim
    """
    with db.engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(chunk_id=r["chunk_id"], text=r["content"], doc_type=r["doc_type"],
                 doc_date=str(r["doc_date"]) if r["doc_date"] else None,
                 title=r["title"], source=r["source_path"], position=r["position"],
                 similarity=round(1 - float(r["distance"]), 3)) for r in rows]


def for_findings(sku: str, weeks: list[str], findings: list[dict], limit: int = 6) -> list[dict]:
    """Documents that could explain a specific set of findings."""
    d = db.load()
    prod = d["products"]
    row = prod[prod.sku == sku]
    if row.empty:
        return []
    p = row.iloc[0]

    types = sorted({t for f in findings
                    for t in FINDING_TO_DOCTYPE.get(f["id"], ["meeting_notes"])})
    return search(query=build_query(sku, findings, prod), weeks=weeks,
                  skus=[sku], models=[p.model], departments=[p.department],
                  doc_types=types, limit=limit)


def external(sku: str, limit: int = 4) -> list[dict]:
    """
    Market news. Only called when the gate opens.

    News never names a SKU, so the search is at category and market level - that
    mapping is what makes this leg return anything useful at all. No week filter:
    news is dated, not period-tagged like internal minutes.
    """
    d = db.load()
    prod = d["products"]
    row = prod[prod.sku == sku]
    if row.empty:
        return []
    p = row.iloc[0]
    q = f"{p.department} {p.model} accessible luxury Singapore retail demand competitor"
    return search(query=q, source_type="external", limit=limit)
