# retrieve.py — line by line

Six functions. Two are one-liners, one builds a search string, one runs the query,
and two are the entry points the diagnostic calls.

---

## The lookup table at the top

```python
FINDING_TO_DOCTYPE = {
    "B1":       ["meeting_notes", "ops_report"],
    "C1/C2":    ["campaign_plan", "meeting_notes"],
    "RESIDUAL": ["campaign_plan", "meeting_notes", "ops_report"],
}
```

**What kind of document can explain what kind of finding.**

If the decomposition found a stock-out (`B1`), the explanation is either a decision
someone made — buying minutes — or a delivery that arrived late — supply chain
report. It is never a campaign plan.

This costs nothing and removes more noise than any tuning of the similarity
threshold. It works because the analysis already told us what kind of cause we are
looking for.

---

## `_vec(v)` — format a vector for Postgres

```python
def _vec(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"
```

pgvector expects a vector literal as the string `[0.123,-0.456,...]`, not a Python
list. This turns 3072 floats into that string, six decimal places each.

It is boring and it is the thing that breaks first if you pass a list straight
through — you get a type error from Postgres, not from Python.

---

## `_embed_query(q)` — turn the search text into numbers

```python
def _embed_query(q: str):
    r = client.embeddings.create(model=EMBED_MODEL, input=[q], dimensions=EMBED_DIMS)
    return r.data[0].embedding
```

One API call, one string in, 3072 floats out.

**It must use the same model and the same dimensions as ingestion.** Embed the
documents with one model and the query with another and every distance is
meaningless — no error, just bad results. That is why both constants sit at the
top of the file and are duplicated from `ingest.py` deliberately rather than
imported, so a mismatch is visible.

---

## `build_query(sku, findings, products)` — write the search text

This is the most important function in the file, and the least obvious.

```python
row = products[products.sku == sku]
parts = [sku]
if not row.empty:
    parts += [row.iloc[0].model, row.iloc[0].department, str(row.iloc[0].colour or "")]
```

Start with the SKU code, then add its model, department and colour. So
`MRL-CB-TAN` becomes `MRL-CB-TAN Marlow Crossbody Bags Tan`.

Why: documents rarely write the code. The buying minutes say "Marlow Crossbody
Tan". Searching only for the code would miss them.

```python
for f in findings:
    if f["id"] == "B1":
        parts += ["replenishment", "reorder", "stock", "out of stock", "delivery"]
    elif f["id"].startswith("C"):
        parts += ["price", "discount", "markdown", "campaign"]
    else:
        parts += ["campaign", "support", "demand", "range"]
```

Now add words for **what the numbers found**, not for what the user asked.

- Stock-out → the vocabulary a supply decision is written in
- Price effect → the vocabulary a pricing decision is written in
- Residual → the vocabulary a campaign or range decision is written in

```python
return " ".join(dict.fromkeys(p for p in parts if p))
```

`dict.fromkeys` removes duplicates while keeping order — the same word can be
added by two findings.

### The point of the whole function

> Searching "why did sales drop" returns documents about sales dropping.
> Semantically perfect, analytically useless.

The user's question is not the search text. **The findings are.** The analysis runs
first precisely so that retrieval knows what to look for.

---

## `search(...)` — the filtered query

The only function that touches the database. Everything else calls it.

```python
where, params = ["d.source_type = :st"], {"st": source_type}
```

Start a list of SQL conditions and a dict of bound parameters. `source_type` is
always applied — internal documents and external news never mix in one search.

### Filter 1 — the time window

```python
if weeks:
    where.append("(c.period_start IS NULL OR c.period_start <= :wmax)")
    where.append("(c.period_end   IS NULL OR c.period_end   >= :wmin)")
    params |= {"wmin": min(weeks), "wmax": max(weeks)}
```

Keep a document if the period it **talks about** overlaps the period being asked
about. Two ranges overlap when each one starts before the other ends.

`IS NULL` passes — a document with no stated period is kept rather than dropped,
because a missing value should not silently remove evidence.

This filter alone usually removes 90% or more.

### Filter 2 — the product

```python
ent = []
if skus:        ent.append("c.entities->'skus'  ?| :skus")
if models:      ent.append("c.entities->'models' ?| :models")
if departments: ent.append("c.entities->'departments' ?| :depts")
if ent:
    where.append("(" + " OR ".join(ent) + " OR d.entities->'skus' ?| :skus)")
```

`?|` is the Postgres JSONB operator for "does this array contain **any** of these
values". `c.entities->'skus'` is the list of SKUs named in that chunk.

The three conditions are joined with `OR` — the chunk qualifies if it names the
SKU, **or** its model, **or** its department. Widening rather than narrowing,
because a passage about Marlow Crossbody is relevant to a question about the Tan
colourway.

The last clause is the important one: `d.entities->'skus'` is the **document**
level list. A chunk saying "deferred to fund the Autumn buy" names no product at
all — but the document it came from does, so it is still found.

### Filter 3 — document type

```python
if doc_types:
    where.append("c.doc_type = ANY(:dt)")
```

From the lookup table at the top. Free, and usually skipped by people building
this.

### Then, and only then, similarity

```python
params["q"] = _vec(_embed_query(query))

sql = f"""
    SELECT c.chunk_id, c.content, c.doc_type, c.doc_date,
           d.title, d.source_path, c.position,
           c.embedding <=> CAST(:q AS vector) AS distance
    FROM doc_chunks c JOIN documents d USING (doc_id)
    WHERE {' AND '.join(where)}
    ORDER BY distance
    LIMIT :lim
"""
```

`<=>` is pgvector's cosine **distance** operator. Smaller is closer, so
`ORDER BY distance` puts the best match first.

The `JOIN documents` brings back the title and file path, which is what makes a
citation possible — a chunk on its own cannot be cited.

**The whole design is this one statement.** Three metadata filters and a
similarity ranking, one round trip, one transaction. With a separate vector
service this would be three network calls and a reconciliation in Python.

```python
similarity=round(1 - float(r["distance"]), 3)
```

Convert distance back to similarity so the caller sees 0.87 meaning "close"
rather than 0.13 meaning "close", which reads backwards.

---

## `for_findings(sku, weeks, findings, limit)` — the diagnostic entry point

```python
types = sorted({t for f in findings
                for t in FINDING_TO_DOCTYPE.get(f["id"], ["meeting_notes"])})
return search(query=build_query(sku, findings, prod), weeks=weeks,
              skus=[sku], models=[p.model], departments=[p.department],
              doc_types=types, limit=limit)
```

Assembles the arguments and calls `search`. Three lines of real work:

1. Collect the document types that could explain **any** of the findings — a set,
   so two findings pointing at meeting notes only search them once
2. Build the search text from the findings
3. Pass the SKU, its model and its department so the product filter can widen

This is what `explain_gap` calls after the decomposition has run.

---

## `external(sku, weeks, limit)` — market news, only when the gate opens

```python
q = f"{p.department} {p.model} accessible luxury Singapore retail demand competitor"
return search(query=q, weeks=None, source_type="external", limit=limit)
```

Two differences from `for_findings`, both deliberate.

**The query is at category and market level, never the SKU.** News says "the
handbag market" and "Charles & Keith". It never says `MRL-CB-TAN`. Searching for
the code returns nothing, every time.

**`weeks=None`** — no time filter. News items carry a publication date but no
"period covered", so filtering on period would drop all of them.

`source_type="external"` keeps this to the news feed, so a campaign plan can never
appear in an answer that is supposed to be about the outside world.
