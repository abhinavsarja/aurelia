"""
search_documents - paste into aurelia/tools.py, below explain_gap.

Then add it to TOOLS:

    TOOLS = [get_sales, rank_products, compare, get_trend, get_stock,
             get_target_source, find_exceptions, search_documents, explain_gap]

Requires:  from aurelia.rag import retrieve
"""

# --- note ------------------------------------------------------------------
# This is the only tool that returns text a person wrote rather than a number a
# query computed, so it carries a rule none of the others need:
#
#   A NUMBER INSIDE A DOCUMENT IS A QUOTE, NOT DATA.
#
# The June buying minutes say Tan "carried roughly 41% of Marlow Crossbody
# volume through May". That is what somebody believed in a meeting. It is not a
# figure from the warehouse, it was not recomputed, and it may simply be wrong.
# Presenting it as a system number would break the one rule the whole design
# rests on. So every figure from a document must be attributed to the document
# and its date, never stated flat.
# ---------------------------------------------------------------------------
def search_documents(query: str, month: str = None, doc_type: str = None,
                     sku: str = None, department: str = None,
                     source_type: str = "internal",
                     limit: int = 5) -> dict:
    """
    Find documents and quote what they say.

    source_type:
      "internal" (default) - meeting notes, campaign plans, ops reports
      "external" - competitor / market news feed

    Use for questions ABOUT documents, decisions, or news:
      "what was decided at the July buying committee"
      "what does the campaign plan say about Marlow"
      "what is the latest news about Charles & Keith"
      "any competitor news on crossbody bags"

    doc_type is one of: campaign_plan, meeting_notes, ops_report, news.
    Leave it out to search everything in that source_type.

    Do NOT use this to look up performance figures. Documents contain numbers
    people wrote down at the time; those are opinions with a date on them, not
    the current data. For any figure, use get_sales, explain_gap or the other
    tools, which read the database.

    Returns passages with the document they came from and its date, so every
    quote can be attributed.
    """
    st = (source_type or "internal").lower().strip()
    if st not in ("internal", "external"):
        return dict(error="source_type must be 'internal' or 'external'")

    skus = models = depts = None
    if sku:
        code = _resolve_sku(sku)
        if code:
            row = _D["products"][_D["products"].sku == code].iloc[0]
            skus, models, depts = [code], [row.model], [row.department]
    elif department:
        depts = [department]

    try:
        hits = retrieve.search(
            query=query, month=month, skus=skus, models=models,
            departments=depts, doc_types=[doc_type] if doc_type else None,
            source_type=st, limit=limit)
    except Exception as e:
        return dict(error=f"{type(e).__name__}: {e}")

    if not hits:
        kind = "news" if st == "external" else "internal document"
        return dict(query=query, month=month, doc_type=doc_type,
                    source_type=st, passages=[],
                    note=f"No {kind} matches that. Say so rather than "
                         "answering from general knowledge.")

    if st == "external":
        hits = sorted(hits, key=lambda h: h.get("doc_date") or "", reverse=True)

    return dict(
        query=query, month=month, doc_type=doc_type, source_type=st,
        passages=[dict(text=h["text"], document=h["title"],
                       written=h["doc_date"], type=h["doc_type"],
                       source=h["source"], similarity=h["similarity"])
                  for h in hits],
        rule=("Any number appearing in these passages is a QUOTE from that "
              "document on that date. Attribute it - 'the June buying minutes "
              "record that...' / 'Business Times reported on 4 Aug...' - and "
              "never present it as a current figure. For real figures use the "
              "data tools."))
