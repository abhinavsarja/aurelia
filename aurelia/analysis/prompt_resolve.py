"""
Builds the exact message sent to the model for the RESOLVE step.

Run this to see the full prompt, verbatim:
    python -m aurelia.analysis.prompt_resolve "what were bag sales last week?"
"""
import sys

from aurelia.analysis.dictionary import build_context

INSTRUCTIONS = """
You convert a business question into structured parameters.

You do NOT answer the question. You do NOT calculate anything. You do not have
the data. Your only job is to fill in the fields below using the reference
material that follows.

Return JSON only, matching this shape:

{
  "type":        one of: lookup | ranking | comparison | trend | diagnostic | provenance | out_of_scope,
  "metric":      one of: revenue | units | margin | sell_through | discount | stock_cover,
  "department":  a department name, or null,
  "model":       a model name, or null,
  "sku":         a SKU code, or null,
  "channel":     "store" | "ecom" | null  (null means both),
  "week":        a single week as YYYY-Www, or null,
  "weeks":       a list of weeks, or null,
  "month":       a month as YYYY-MM, or null,
  "compare_to":  what to measure against: "target" | "previous" | "last_year" | null,
  "limit":       a number for ranking questions, or null,
  "unresolved":  a list of anything in the question you could NOT map with
                 confidence. Leave it empty only if you resolved everything.
}

Rules:
- Use ONLY names that appear in the reference material below. Never invent a
  department, model or SKU.
- If a product name is ambiguous, put it in "unresolved" and leave the field null.
  Do not guess which one was meant.
- If the question asks about a period with no data, set type to "out_of_scope".
- If the question asks for a forecast, a prediction, or a recommendation to act,
  set type to "out_of_scope".
- "type": "diagnostic" is only for questions asking WHY something changed.
"""

def build(question: str) -> str:
    return (INSTRUCTIONS.strip()
            + "\n\n" + "=" * 68 + "\nREFERENCE MATERIAL\n" + "=" * 68 + "\n\n"
            + build_context()
            + "\n\n" + "=" * 68 + "\nQUESTION\n" + "=" * 68 + "\n\n"
            + question.strip() + "\n")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "what were bag sales last week?"
    print(build(q))
