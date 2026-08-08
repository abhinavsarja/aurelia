"""FastAPI service. Health, ask, and reload."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from aurelia import db
from aurelia.agent import Agent
from aurelia.analysis.dictionary import build_context
from aurelia.tools import TOOLS

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_agent: Agent | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _agent
    db.load()
    _agent = Agent(TOOLS, build_context())
    log.info("agent ready")
    yield


app = FastAPI(title="AURELIA", version="0.1", lifespan=lifespan)


class Ask(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", **db.meta()}


@app.post("/ask")
def ask(body: Ask):
    if not body.question.strip():
        raise HTTPException(400, "empty question")
    return _agent.ask(body.question)


@app.post("/reload")
def reload():
    """Call after a weekly publish."""
    db.load(force=True)
    return {"reloaded": True, **db.meta()}
