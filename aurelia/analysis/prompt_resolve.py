"""
Print the exact message sent to the model for the resolve step.

    python3 -m aurelia.analysis.prompt_resolve "what were bag sales last week?"

Uses the database when it is reachable, the CSVs otherwise, and says which - the
reference material is only correct if it came from the same place the tools read.
"""
import sys

from aurelia.analysis.dictionary import build_context

INSTRUCTIONS = """
You convert a business question into structured parameters.

You do NOT answer the question. You do NOT calculate anything. You do not have
the data. Your only job is to fill in the fields using the reference material
that follows.

Use ONLY names that appear in the reference material. Never invent a department,
model or SKU, and never construct a SKU code from a product name.
""".strip()


def build(question: str, data=None) -> str:
    return (INSTRUCTIONS + "\n\n" + "=" * 68 + "\nREFERENCE MATERIAL\n" + "=" * 68
            + "\n\n" + build_context(data)
            + "\n\n" + "=" * 68 + "\nQUESTION\n" + "=" * 68 + "\n\n"
            + question.strip() + "\n")


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "what were bag sales last week?"
    data = None
    try:
        from aurelia import db
        data = db.load()
        source = "postgres"
    except ModuleNotFoundError as e:
        sys.exit(
            f"Missing package {e.name!r} in {sys.executable}.\n"
            f"Install the project here (`pip install -e .`) or run with "
            f"python3 (the interpreter uvicorn uses)."
        )
    except Exception as e:
        source = f"csv fallback ({type(e).__name__}: {e})"

    print(build(q, data))
    print(f"[reference material built from: {source}]")
