"""
Run the golden set.

    python tests/run_golden.py                 # everything
    python tests/run_golden.py --only D        # just the diagnostics
    python tests/run_golden.py --tools-only    # tool selection, no answer generation (cheap)

Two things are measured and they fail differently:

  tool selection  - did the right function fire? A wrong tool means a wrong
                    answer even when the prose reads well.
  behaviour       - did it answer, refuse, clarify or correct the premise as
                    expected? This is where a system embarrasses itself.
"""
from __future__ import annotations
import json, sys, argparse, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from aurelia import db
from aurelia.agent import Agent
from aurelia.analysis.dictionary import build_context
from aurelia.tools import TOOLS

GOLD = json.loads((pathlib.Path(__file__).parent / "golden_set.json").read_text())


def classify(r: dict) -> str:
    """What did the system actually do?"""
    a = (r.get("answer") or "").lower()
    if r["tool_calls"]:
        if any(w in a for w in ["did not", "does not", "actually rose", "actually up",
                                "beat target", "ahead of target", "not a collapse"]):
            return "correct_premise"
        return "answer"
    # a refusal that helpfully offers alternatives still contains "which" and
    # "please specify", so refusal has to be tested for first
    refusing = any(w in a for w in [
        "i don't have", "i do not have", "no data", "not available", "out of scope",
        "does not make decisions", "cannot predict", "can't predict", "does not predict",
        "in the future", "beyond", "only have data"])
    if refusing:
        return "refuse"
    if any(w in a for w in ["did you mean", "which one", "there are three",
                            "please specify which", "could you clarify"]):
        return "clarify"
    return "refuse"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="filter by id prefix, e.g. D")
    ap.add_argument("--tools-only", action="store_true")
    args = ap.parse_args()

    db.load()
    agent = Agent(TOOLS, build_context())

    qs = GOLD["questions"]
    if args.only:
        qs = [q for q in qs if q["id"].startswith(args.only)]

    tool_ok = beh_ok = content_ok = content_n = 0
    fails, t0 = [], time.time()

    for q in qs:
        r = agent.ask(q["q"])
        called = r["tool_calls"][0]["tool"] if r["tool_calls"] else None
        beh = classify(r)

        t_ok = (called == q["tool"])
        b_ok = (beh == q["behaviour"])
        tool_ok += t_ok
        beh_ok += b_ok

        c_ok = True
        if q.get("must_include"):
            content_n += 1
            missing = [s for s in q["must_include"] if s.lower() not in (r["answer"] or "").lower()]
            c_ok = not missing
            content_ok += c_ok

        gate_ok = True
        if "gate_opened" in q and r["tool_results"]:
            actual = r["tool_results"][0].get("gate_opened")
            gate_ok = (actual == q["gate_opened"])

        mark = "PASS" if (t_ok and b_ok and c_ok and gate_ok) else "FAIL"
        print(f"{mark}  {q['id']}  {q['q'][:52]:54s} tool={str(called):16s} {beh}")
        if mark == "FAIL":
            fails.append(dict(id=q["id"], question=q["q"],
                              expected_tool=q["tool"], got_tool=called,
                              expected_behaviour=q["behaviour"], got_behaviour=beh,
                              gate_ok=gate_ok, answer=r["answer"],
                              note=q.get("note", "")))

    n = len(qs)
    print("\n" + "=" * 74)
    print(f"tool selection   {tool_ok}/{n}   {tool_ok/n:.0%}")
    print(f"behaviour        {beh_ok}/{n}   {beh_ok/n:.0%}")
    if content_n:
        print(f"required content {content_ok}/{content_n}   {content_ok/content_n:.0%}")
    print(f"elapsed          {time.time()-t0:.0f}s")

    if fails:
        print(f"\n{len(fails)} to look at:\n")
        for f in fails:
            print(f"  {f['id']}  {f['question']}")
            print(f"      expected {f['expected_tool']} / {f['expected_behaviour']}")
            print(f"      got      {f['got_tool']} / {f['got_behaviour']}")
            if f["note"]:
                print(f"      why it matters: {f['note']}")
            print(f"      answer: {(f['answer'] or '')[:170]}")
            print()

    pathlib.Path(ROOT / "tests" / "golden_results.json").write_text(
        json.dumps(dict(total=n, tool_selection=tool_ok, behaviour=beh_ok,
                        failures=fails), indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
