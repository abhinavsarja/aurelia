"""
Chainlit test harness.

    chainlit run chainlit_app.py -w

Shows the tool that was chosen and the arguments alongside the answer, which is
the thing you actually need while building - a wrong answer is usually a wrong
tool choice, and that is invisible if you only see the prose.
"""
import json
from pathlib import Path

import chainlit as cl
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from aurelia import db
from aurelia.agent import Agent
from aurelia.analysis.dictionary import build_context
from aurelia.tools import TOOLS

_agent = None


@cl.on_chat_start
async def start():
    global _agent
    db.load()
    m = db.meta()
    _agent = Agent(TOOLS, build_context())
    await cl.Message(
        content=(f"**AURELIA**  ·  {m['skus']} SKUs  ·  {m['weeks']} weeks  "
                 f"({m['first_week']} to {m['latest_week']})\n\n"
                 "Try: *what were bag sales last week* · *which models are behind target in July* · "
                 "*why did MRL-CB-TAN drop last month*")).send()


@cl.on_message
async def on_message(msg: cl.Message):
    async with cl.Step(name="thinking") as step:
        r = await cl.make_async(_agent.ask)(msg.content)
        step.output = json.dumps(r["tool_calls"], indent=2) or "no tool called"

    for c, res in zip(r["tool_calls"], r["tool_results"]):
        async with cl.Step(name=c["tool"], type="tool") as s:
            s.input = json.dumps(c["arguments"], indent=2)
            s.output = json.dumps(res, indent=2, default=str)[:3000]

    await cl.Message(content=f"{r['answer']}\n\n`{r['latency_ms']}ms`").send()
