"""
The loop.

    question -> model picks a tool -> we validate and run it -> model writes the answer

The model proposes; this module disposes. Every tool call is validated before it
runs, and every number in the final answer came out of a function, not the model.
"""
from __future__ import annotations
import json, time, inspect, logging
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI

from aurelia.jsonutil import jsonable

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

log = logging.getLogger(__name__)
_client: OpenAI | None = None
MODEL = "gpt-5-mini"


def _openai() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

SYSTEM = """
You answer questions about retail trading performance for senior management about a company called Aurelia.

## The rule that matters most
You have no data. Every number you give must come from a tool result. Never
estimate, never round to a "roughly", never infer a figure that was not returned.

## Choosing a tool
Choose exactly one tool unless the question genuinely needs two.

Use the tool. Do not ask the user to supply an argument that has a default or
that you can work out from the reference material. "How are bags doing" is
answerable - use the latest week and say which period you used. Only ask when a
product name genuinely matches more than one product.

SKU codes must be copied exactly from the SKU list. Never build a code from a
product name.

For questions about meetings, decisions, minutes, campaign plans, or what
someone said in a document, use search_documents with source_type="internal"
and if they are asking about competitors or about events that are happening outside Aurelia, 
search with doc_type="external".
Pass month when the user names one (e.g. July → "2026-07") and
doc_type="meeting_notes" for meeting questions.

For competitor, market, or "latest news" questions, use search_documents with
source_type="external" (and doc_type="news" when appropriate). Lead with the
most recent item. Quote and attribute; never treat document figures as live data.

If no tool fits, say so plainly and say what you could show instead.
If the question asks for a forecast or a recommendation to act, decline - this
system explains what happened, it does not predict or decide.

## Writing the answer
You are not reporting the data back. You are telling a busy person what it means.

- If the result contains a comparison against target, against the previous
  period, or against last year, you MUST include it. A number without its
  comparison is not an answer.
- Lead with what is unusual. If everything is normal, say that and stop.
- Where a total hides an important difference between its parts, say so. "1,001
  units in stock" is misleading if one colour is at zero.
- Use the unit that makes a number meaningful. Weeks of cover, not just units on
  hand. Percent against target, not just revenue.
- If a figure needs a caveat the tool provided - low confidence, a small sample,
  a category-wide effect - give the caveat. Do not quietly drop it.
- Do not invent a cause. If the tool did not identify why something happened,
  do not supply a reason.
- If the question assumes something the numbers contradict, say so before
  answering. A product described as "collapsing" that is down 8%, or "doing
  badly" when it beat target, needs correcting, not explaining.
- When a tool returns several findings, report the ones that matter, not only
  the largest. A small problem nobody can see elsewhere is worth more than a
  big one already visible on a sales report.

Keep it to three or four sentences. Currency is SGD, written S$.
""".strip()


def _schema(fn) -> dict:
    """Turn a function into a tool definition. Docstring becomes the description."""
    props, required = {}, []
    for name, p in inspect.signature(fn).parameters.items():
        ann = p.annotation
        t = ("array" if getattr(ann, "__origin__", None) is list else
             "integer" if ann is int else "string")
        props[name] = {"type": t}
        if t == "array":
            props[name]["items"] = {"type": "string"}
        if p.default is inspect._empty:
            required.append(name)
    return {"type": "function", "function": {
        "name": fn.__name__,
        "description": inspect.getdoc(fn),
        "parameters": {"type": "object", "properties": props, "required": required}}}


class Agent:
    def __init__(self, tools: list, dictionary: str):
        self.registry = {f.__name__: f for f in tools}
        self.schemas = [_schema(f) for f in tools]
        self.dictionary = dictionary

    def ask(self, question: str) -> dict:
        t0 = time.time()
        msgs = [{"role": "system", "content": SYSTEM + "\n\n" + self.dictionary},
                {"role": "user", "content": question}]

        first = _openai().chat.completions.create(
            model=MODEL, messages=msgs, tools=self.schemas, tool_choice="auto")
        msg = first.choices[0].message
    
        calls, results = [], []
        if msg.tool_calls:
            msgs.append(msg.model_dump(exclude_none=True))
            for c in msg.tool_calls:
                name = c.function.name
                args = json.loads(c.function.arguments or "{}")
                args = {k: v for k, v in args.items() if v is not None}

                if name not in self.registry:            # cannot invent a tool
                    out = {"error": f"no such tool: {name}"}
                else:
                    try:
                        out = jsonable(self.registry[name](**args))
                    except Exception as e:               # a bad argument fails loudly
                        out = {"error": f"{type(e).__name__}: {e}"}

                calls.append({"tool": name, "arguments": args})
                results.append(out)
                msgs.append({"role": "tool", "tool_call_id": c.id,
                             "content": json.dumps(out, default=str)})

            second = _openai().chat.completions.create(model=MODEL, messages=msgs)
            answer = second.choices[0].message.content
        else:
            answer = msg.content        # declined, or asked for clarification

        final = jsonable(dict(question=question, answer=answer,
                             tool_calls=calls, tool_results=results,
                             latency_ms=int((time.time() - t0) * 1000)))
        
        
        return final