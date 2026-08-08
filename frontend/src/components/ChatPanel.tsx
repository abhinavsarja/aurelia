import { useEffect, useRef, useState, type FormEvent } from "react";
import { askQuestion } from "../lib/ask";
import type { AssistantPayload, ChatMessage } from "../types";

const SUGGESTIONS = [
  "what were bag sales last week",
  "which models are behind target in July",
  "why did MRL-CB-TAN drop last month",
];

function AssistantBody({ payload }: { payload: AssistantPayload }) {
  return (
    <div className="body">
      <div className="hdl" style={{ whiteSpace: "pre-wrap", fontWeight: 500 }}>
        {payload.headline}
      </div>
      {payload.plain && <p>{payload.plain}</p>}
      {payload.tools && payload.tools.length > 0 && (
        <div className="meta-line mut">
          tool{payload.tools.length > 1 ? "s" : ""}: {payload.tools.join(", ")}
        </div>
      )}
      {payload.latencyMs != null && (
        <div className="meta-line mut">{payload.latencyMs}ms</div>
      )}
    </div>
  );
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const uid = `u-${Date.now()}`;
    setMessages((m) => [...m, { id: uid, role: "user", text: q }]);
    setInput("");
    setBusy(true);
    try {
      const payload = await askQuestion(q);
      setMessages((m) => [
        ...m,
        { id: `a-${Date.now()}`, role: "assistant", payload },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          payload: {
            headline: "Could not reach /ask.",
            plain:
              (err instanceof Error ? err.message : String(err)) +
              " — is FastAPI running on :8001?",
          },
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <aside className="chat">
      <div className="chat-hd">
        <h3>Ask Aurelia</h3>
        <p>Live answers from POST /ask</p>
      </div>
      <div className="chat-body" ref={bodyRef}>
        {messages.length === 0 && !busy && (
          <div className="typing">Ask a question to query the trading data.</div>
        )}
        {messages.map((msg) =>
          msg.role === "user" ? (
            <div className="msg u" key={msg.id}>
              <div>{msg.text}</div>
            </div>
          ) : (
            <div className="msg a" key={msg.id}>
              <AssistantBody payload={msg.payload} />
            </div>
          ),
        )}
        {busy && <div className="typing">Thinking…</div>}
      </div>
      <div className="suggest">
        {SUGGESTIONS.map((s) => (
          <button
            type="button"
            className="sg"
            key={s}
            disabled={busy}
            onClick={() => void send(s)}
          >
            {s}
          </button>
        ))}
      </div>
      <form className="chat-in" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about any product, department or week…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </aside>
  );
}
