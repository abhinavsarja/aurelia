"""
The loop.

    question -> model picks a tool -> we validate and run it -> model writes the answer

The model proposes; this module disposes. Every tool call is validated before it
runs, and every number in the final answer came out of a function, not the model.

The loop also guarantees a response contract. Every call to ask() ends in exactly
one of three states, never anything else:

    1. a non-empty answer written from tool results
    2. an explicit refusal or clarifying question
    3. a degraded answer rendered from the tool result, and flagged as such

An empty answer is a failure state, not an answer. That is enforced here rather
than hoped for in the prompt.
"""
from __future__ import annotations
import json, time, inspect, logging
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints
from dotenv import load_dotenv
from openai import OpenAI

from aurelia.jsonutil import jsonable

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

log = logging.getLogger(__name__)
_client: OpenAI | None = None
MODEL = "gpt-5-mini"
MAX_ROUNDS = 3

# A backstop, not the primary check. The structural test is "no tool ran"; this
# only distinguishes a promise from a legitimate refusal, which also runs no tool.
# Deliberately first-person and future tense - "let me know if you want the SKU
# breakdown" is a good closing line, not a promise, and must not match.
PROMISES = ("one moment", "one sec", "hold on", "give me a moment",
            "i'll check", "i'll fetch", "i'll pull", "i'll run", "i'll look",
            "i'll get", "i will check", "i will fetch",
            "let me pull", "let me check", "let me run", "let me look",
            "fetching", "checking now")


def _openai() -> OpenAI:
    global _client
    if _client is None:
        # Bound hangs - default httpx wait can sit forever on a stuck TLS read.
        _client = OpenAI(timeout=90.0, max_retries=2)
    return _client


def _text(msg) -> str:
    """Message content, normalised. None and whitespace both become ''."""
    return (getattr(msg, "content", None) or "").strip()


def _coerce(fn, args: dict) -> dict:
    """
    Make the arguments match the signature before the function sees them.

    The schema says limit is an integer and the model still sends "10" perhaps
    one time in three. Downstream that becomes `[:"10"]` or `"10" // 3`, which
    raises a TypeError deep inside the tool, and the model then writes a fluent
    paragraph around a crash. Converting here is cheaper than defending in nine
    separate functions.

    Annotations are resolved via get_type_hints so this still works when the
    tool modules use from __future__ import annotations (where inspect shows
    'int' as a string, and `ann is int` would silently fail).
    """
    hints = get_type_hints(fn)
    out = {}
    for k, v in args.items():
        ann = hints.get(k)
        origin = get_origin(ann) or ann
        if origin is int and isinstance(v, str):
            try: v = int(v.strip())
            except ValueError: pass
        elif origin is float and isinstance(v, str):
            try: v = float(v.strip())
            except ValueError: pass
        elif origin is list and isinstance(v, str):
            v = [x.strip() for x in v.split(",") if x.strip()]
        out[k] = v
    return out


def _render(call: dict, result: Any) -> str:
    """
    Last resort, when the model returns nothing at all.

    We already hold the tool result, so there is no reason to show a blank panel.
    Deliberately unpolished - it should be obvious that this is a fallback and
    not the system working as intended.
    """
    body = json.dumps(result, default=str)
    if len(body) > 700:
        body = body[:700] + " ..."
    return (f"I ran {call['tool']}({json.dumps(call['arguments'], default=str)}) "
            f"but could not write a summary of the result. Raw output: {body}")


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
Pass month when the user names one (e.g. July -> "2026-07") and
doc_type="meeting_notes" for meeting questions.

For competitor, market, or "latest news" questions, use search_documents with
source_type="external" (and doc_type="news" when appropriate). Lead with the
most recent item. Quote and attribute; never treat document figures as live data.

If no tool fits, say so plainly and say what you could show instead.
If the question asks for a forecast or a recommendation to act, decline - this
system explains what happened, it does not predict or decide.

Never output JSON, tool arguments, or a promise to fetch something.
If you need a tool, call it. The user sees only your final sentences.

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
    hints = get_type_hints(fn)
    props, required = {}, []
    for name, p in inspect.signature(fn).parameters.items():
        ann = hints.get(name, p.annotation)
        origin = get_origin(ann) or ann
        t = ("array" if origin is list else
             "integer" if origin is int else
             "number" if origin is float else "string")
        props[name] = {"type": t}
        if t == "array":
            item = get_args(ann)[0] if get_args(ann) else str
            item_origin = get_origin(item) or item
            props[name]["items"] = {
                "type": ("integer" if item_origin is int else
                         "number" if item_origin is float else "string")}
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

    def _call(self, msgs, *, tools=False, tool_choice=None):
        kw = {"model": MODEL, "messages": msgs}
        if tools:
            kw["tools"] = self.schemas
            if tool_choice:
                kw["tool_choice"] = tool_choice
        return _openai().chat.completions.create(**kw).choices[0].message

    def _run_calls(self, msg, msgs, calls, results, seen) -> bool:
        """
        Execute every tool the model asked for, and append the results.

        Mutates msgs, calls and results in place. Used by both the normal loop
        and the forced retry, so the validation cannot drift between the two.

        Returns True if at least one call was new. A round that only repeats
        earlier calls has produced no information, and looping again would only
        spend money to arrive at the same place.
        """
        # The assistant's own narration is dropped before the message is stored.
        # Left in, the model reads "I'll fetch that now" on the next round, treats
        # the turn as already spoken, and returns empty content.
        m = msg.model_dump(exclude_none=True)
        m.pop("content", None)
        msgs.append(m)

        progressed = False
        for c in msg.tool_calls:
            name = c.function.name
            args = json.loads(c.function.arguments or "{}")
            args = {k: v for k, v in args.items() if v is not None}
            sig = (name, json.dumps(args, sort_keys=True, default=str))
            repeat = sig in seen

            if repeat:                                 # asked for twice, run once
                out = {"note": "identical call already made; see the earlier result"}
            elif name not in self.registry:            # cannot invent a tool
                out = {"error": f"no such tool: {name}"}
            else:
                fn = self.registry[name]
                args = _coerce(fn, args)               # "10" -> 10 before it hurts
                try:
                    out = jsonable(fn(**args))
                except Exception as e:                 # a bad argument fails loudly
                    out = {"error": f"{type(e).__name__}: {e}"}

            if not repeat:
                seen.add(sig)
                progressed = True
                calls.append({"tool": name, "arguments": args})
                results.append(out)

            # every tool_call_id must be answered, repeat or not, or the next
            # request is rejected as malformed
            msgs.append({"role": "tool", "tool_call_id": c.id,
                         "content": json.dumps(out, default=str)})

        return progressed

    def ask(self, question: str) -> dict:
        t0 = time.time()
        msgs = [{"role": "system", "content": SYSTEM + "\n\n" + self.dictionary},
                {"role": "user", "content": question}]

        calls, results, seen = [], [], set()
        answer, degraded = None, None

        msg = self._call(msgs, tools=True, tool_choice="auto")

        # Loop rather than a single round. A question like "which model is worst,
        # and how much stock does it have" needs the second call to depend on the
        # first result.
        for _ in range(MAX_ROUNDS):
            if not msg.tool_calls:
                answer = _text(msg)
                break
            if not self._run_calls(msg, msgs, calls, results, seen):
                break                                  # no new information
            msg = self._call(msgs, tools=True)

        if answer is None:                             # ran out of rounds
            answer = _text(self._call(msgs))

        # --- the response contract ---------------------------------------
        # Three failure modes, each with its own recovery. They are ordered:
        # get a tool to run, then get a sentence written, then give up loudly.

        # 1. No tool ran. Either the model announced a step instead of taking it,
        #    or it returned nothing. A genuine refusal - "I can't advise who to
        #    fire" - also runs no tool, and must be left alone, which is what the
        #    PROMISES check is for.
        if not calls and (not answer or any(p in answer.lower() for p in PROMISES)):
            log.info("forcing a tool call; model replied %r",
                     (answer or "")[:80] or "<empty>")
            msg = self._call(msgs, tools=True, tool_choice="required")
            if msg.tool_calls:
                self._run_calls(msg, msgs, calls, results, seen)
                answer = _text(self._call(msgs))

        # 2. Tools ran but nothing was written. Ask once more, plainly, with no
        #    tools available so the only thing left to do is answer.
        if not answer and results:
            msgs.append({"role": "user",
                         "content": "Write the answer now, from the tool results "
                                    "above. Three or four sentences. Do not call "
                                    "a tool."})
            answer = _text(self._call(msgs))

        # 3. Still nothing. Never return a blank panel.
        if not answer:
            if results:
                answer = _render(calls[-1], results[-1])
                degraded = "model returned no text; rendered from the tool result"
            else:
                answer = ("I could not answer that. Please rephrase, or name a "
                          "product, department or period.")
                degraded = "model returned no text and no tool ran"
            log.warning("degraded answer for %r: %s", question, degraded)

        return jsonable(dict(question=question, answer=answer,
                             tool_calls=calls, tool_results=results,
                             degraded=degraded,
                             latency_ms=int((time.time() - t0) * 1000)))
