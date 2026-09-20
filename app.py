"""
City Intelligence: a Streamlit front end for the LangChain weather + news agent.

Run:
    streamlit run app.py

Expects your agent code to live in `agent.py` (same folder) and to expose
a variable called `agent` (and optionally `llm`, used only to show the model name).
"""

import html
import os
import time
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="City Intelligence",
    page_icon=":material/location_city:",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASSISTANT_AVATAR = ":material/location_city:"
USER_AVATAR = ":material/person:"

SERVICES = [
    ("Groq model", "GROQ_API_KEY"),
    ("OpenWeather", "OPENWEATHER_API_KEY"),
    ("Tavily search", "TAVILY_API_KEY"),
]

SUGGESTIONS = [
    "Give me a full briefing for Hyderabad",
    "What's the weather in Mumbai right now?",
    "What's the latest news in Delhi?",
    "Compare the weather in Chennai and Bengaluru",
]

QUICK_PROMPTS = {
    "briefing": "Give me a full city briefing for {city}",
    "weather": "What's the current weather in {city}?",
    "news": "What's the latest news in {city}?",
}

# Tool name -> (label shown in the lookup log, icon key)
TOOLS = {
    "get_weather": ("Weather", "weather"),
    "get_news": ("News", "news"),
}


def _svg(paths: str) -> str:
    return (
        '<svg class="log-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{paths}</svg>'
    )


ICONS = {
    "weather": _svg(
        '<path d="M12 2v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="M20 12h2"/>'
        '<path d="m19.07 4.93-1.41 1.41"/><path d="M15.947 12.65a4 4 0 0 0-5.925-4.128"/>'
        '<path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6Z"/>'
    ),
    "news": _svg(
        '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>'
        '<path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/>'
    ),
    "tool": _svg(
        '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
    ),
}

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700;800&display=swap');

:root {
  --ci-line: rgba(120,138,152,.32);
  --ci-tint: rgba(120,138,152,.10);
  --ci-accent: #1F5FBF;
  --ci-amber: #E39A00;
  --ci-green: #2A7D4F;
  --ci-red: #C43D2F;
}

html, body, .stApp, .stMarkdown, [data-testid="stSidebar"],
[data-testid="stChatInput"] textarea, .stTextInput input, .stButton button {
  font-family: 'Schibsted Grotesk', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}

footer { visibility: hidden; }
.block-container { max-width: 800px; padding-top: 2.75rem; padding-bottom: 6rem; }

/* ---- Masthead ---- */
div.masthead { margin: 0 0 1.5rem; }
div.masthead .dateline { font-size: .95rem; font-weight: 600; color: var(--ci-accent); margin-bottom: .5rem; }
div.masthead h1.mast-title {
  font-size: 2.9rem; line-height: 1.04; font-weight: 800; letter-spacing: -.035em;
  margin: 0 0 .9rem; padding: 0; max-width: 16ch; text-wrap: balance;
}
div.masthead .mast-sub { font-size: 1.05rem; line-height: 1.55; max-width: 46ch; opacity: .78; margin: 0; }
div.masthead.compact { margin-bottom: .75rem; }
div.masthead.compact .dateline { font-size: .85rem; margin-bottom: .15rem; }
div.masthead.compact h1.mast-title { font-size: 1.6rem; letter-spacing: -.025em; max-width: none; margin: 0; }
div.masthead.compact .mast-sub { display: none; }

/* ---- Suggestions: ruled list rows ---- */
.list-label { font-size: .9rem; font-weight: 600; opacity: .7; margin: 2.25rem 0 .35rem; }
.st-key-suggestions { gap: 0 !important; border-top: 1px solid var(--ci-line); }
[class*="st-key-sug_"] button {
  width: 100%; justify-content: flex-start; text-align: left;
  background: transparent; border: 0; border-bottom: 1px solid var(--ci-line);
  border-radius: 0; box-shadow: none; padding: .9rem .25rem;
  font-size: 1.05rem; font-weight: 600; color: inherit;
}
[class*="st-key-sug_"] button:hover { background: var(--ci-tint); color: var(--ci-accent); border-bottom-color: var(--ci-line); }

/* ---- Sidebar ---- */
[data-testid="stSidebar"] .stButton button { width: 100%; }
.brand { font-size: 1.3rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.1; }
.brand-sub { font-size: .9rem; opacity: .7; margin-top: .25rem; }
.side-h { font-size: .92rem; font-weight: 700; margin: 1.5rem 0 .5rem; }
.svc { display: flex; align-items: center; gap: .55rem; padding: .3rem 0; font-size: .92rem; }
.svc .note { margin-left: auto; opacity: .65; font-size: .85rem; }

/* ---- Status dots ---- */
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--ci-line); flex: none; }
.dot.ok { background: var(--ci-green); }
.dot.err { background: var(--ci-red); }
.dot.run { background: var(--ci-amber); animation: ci-pulse 1.1s ease-in-out infinite; }
@keyframes ci-pulse { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .dot.run { animation: none; } }

/* ---- Lookup log (inside the status widget) ---- */
.log-wait { display: flex; align-items: center; gap: .55rem; font-size: .92rem; opacity: .8; padding: .25rem 0 .5rem; }
.log { display: flex; flex-direction: column; }
.log-row { padding: .6rem 0; border-bottom: 1px solid var(--ci-line); }
.log-row:last-child { border-bottom: 0; padding-bottom: .2rem; }
.log-head { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.log-ico { width: 17px; height: 17px; flex: none; opacity: .8; }
.log-name { font-weight: 700; }
.log-args { opacity: .7; font-size: .9rem; }
.log-state { margin-left: auto; display: inline-flex; align-items: center; gap: .45rem; font-size: .88rem; font-variant-numeric: tabular-nums; }
.log details { margin: .45rem 0 0 1.65rem; }
.log summary { cursor: pointer; font-size: .86rem; opacity: .75; }
.log-out {
  margin-top: .45rem; padding: .65rem .8rem; background: var(--ci-tint); border-radius: 8px;
  font-size: .86rem; line-height: 1.55; max-height: 220px; overflow: auto; word-break: break-word;
}

/* ---- Chat ---- */
[data-testid="stChatMessage"] { background: transparent; padding: .6rem 0; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--ci-tint); border-radius: 14px; padding: .75rem 1rem;
}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { line-height: 1.62; max-width: 70ch; }
[data-testid="stChatMessage"] h2 { font-size: 1.15rem; font-weight: 700; letter-spacing: -.01em; margin: 1.2rem 0 .4rem; padding: 0; }
[data-testid="stChatMessage"] h3 { font-size: 1rem; font-weight: 700; margin: 1rem 0 .3rem; padding: 0; }
[data-testid="stChatMessage"] a { color: var(--ci-accent); text-underline-offset: 2px; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Agent loading
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Starting the agent…")
def load_agent():
    import importlib

    module = importlib.import_module("agent")
    return module.agent, getattr(module, "llm", None)


agent = None
llm = None
load_error = None
try:
    agent, llm = load_agent()
except Exception as exc:  # missing keys, missing file, bad import, etc.
    load_error = exc

# ---------------------------------------------------------------------------
# Session state + callbacks
# ---------------------------------------------------------------------------

st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending", None)
st.session_state.setdefault("notice", None)


def queue_prompt(text: str) -> None:
    st.session_state.pending = text


def queue_city(kind: str) -> None:
    city = (st.session_state.get("city") or "").strip()[:60]
    if not city:
        st.session_state.notice = "Enter a city name first."
        return
    st.session_state.pending = QUICK_PROMPTS[kind].format(city=city)


def new_chat() -> None:
    st.session_state.messages = []
    st.session_state.pending = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="brand">City Intelligence</div>'
        '<div class="brand-sub">Live weather and news</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="side-h">Look up a city</div>', unsafe_allow_html=True)
    st.text_input("City", key="city", placeholder="e.g. Hyderabad", label_visibility="collapsed")
    st.button(
        "Full briefing", key="act_briefing", type="primary",
        icon=":material/location_city:", on_click=queue_city, args=("briefing",),
    )
    st.button(
        "Weather only", key="act_weather",
        icon=":material/partly_cloudy_day:", on_click=queue_city, args=("weather",),
    )
    st.button(
        "News only", key="act_news",
        icon=":material/newspaper:", on_click=queue_city, args=("news",),
    )
    if st.session_state.notice:
        st.warning(st.session_state.notice, icon=":material/info:")
        st.session_state.notice = None

    st.markdown('<div class="side-h">Connections</div>', unsafe_allow_html=True)
    missing = 0
    rows = []
    for label, env_name in SERVICES:
        found = bool(os.getenv(env_name))
        missing += 0 if found else 1
        rows.append(
            f'<div class="svc"><span class="dot {"ok" if found else "err"}"></span>{label}'
            f'<span class="note">{"Key found" if found else "Key missing"}</span></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)
    if missing:
        st.caption("Add missing keys to your .env file, then restart the app.")

    if llm is not None:
        name = getattr(llm, "model_name", None) or getattr(llm, "model", None)
        if name:
            st.caption(f"Model: {name}")

    st.markdown('<div class="side-h">Conversation</div>', unsafe_allow_html=True)
    st.button("New chat", key="act_new", icon=":material/add:", on_click=new_chat)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def message_text(msg) -> str:
    """Plain text of a LangChain message (content can be a str or a list of blocks)."""
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()


def log_html(events: list) -> str:
    """The lookup log: one row per tool call, single-line HTML so markdown leaves it alone."""
    rows = []
    for e in events:
        label, icon = TOOLS.get(e["name"], (e["name"], "tool"))
        args = ", ".join(f"{k}: {v}" for k, v in (e.get("args") or {}).items())
        if e["status"] == "running":
            state = '<span class="log-state"><span class="dot run"></span>Running</span>'
        elif e["status"] == "error":
            state = '<span class="log-state"><span class="dot err"></span>Failed</span>'
        else:
            state = f'<span class="log-state"><span class="dot ok"></span>Done in {e["seconds"]:.1f}s</span>'
        details = ""
        if e.get("result"):
            body = html.escape(e["result"]).replace("\n", "<br>")
            details = f'<details><summary>Raw output</summary><div class="log-out">{body}</div></details>'
        rows.append(
            f'<div class="log-row"><div class="log-head">{ICONS[icon]}'
            f'<span class="log-name">{html.escape(label)}</span>'
            f'<span class="log-args">{html.escape(args)}</span>{state}</div>{details}</div>'
        )
    return '<div class="log">' + "".join(rows) + "</div>"


def summary_label(events: list, elapsed: float) -> str:
    if not events:
        return f"Answered directly in {elapsed:.1f}s"
    names = list(dict.fromkeys(TOOLS.get(e["name"], (e["name"],))[0].lower() for e in events))
    count = len(events)
    return f"Made {count} lookup{'s' if count != 1 else ''} ({', '.join(names)}) in {elapsed:.1f}s"


def live_label(events: list) -> str:
    running = list(dict.fromkeys(TOOLS.get(e["name"], (e["name"],))[0].lower() for e in events if e["status"] == "running"))
    return f"Looking up {' and '.join(running)}" if running else "Writing the answer"


def model_history() -> list:
    """Conversation so far, minus turns that ended in an error, so follow-ups keep context."""
    msgs = st.session_state.messages
    out = []
    for i, m in enumerate(msgs):
        nxt = msgs[i + 1] if i + 1 < len(msgs) else None
        if m.get("error"):
            continue
        if m["role"] == "user" and nxt and nxt.get("error"):
            continue
        out.append({"role": m["role"], "content": m["content"]})
    return out[-20:]


def explain_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "rate limit" in text or "429" in text:
        return "The Groq API rate limit was reached. Wait a moment, then send your question again."
    if "api key" in text or "api_key" in text or "401" in text or "authentication" in text:
        return "The model rejected the request. Check GROQ_API_KEY in your .env file."
    if "tool_use_failed" in text or "failed to call a function" in text or "tool call" in text:
        return "The model produced a malformed tool call. Send your question again or rephrase it."
    return "The agent stopped with an error. Send your question again."


def consume_update(update: dict, events: list, out: dict) -> None:
    """Fold one LangGraph 'updates' chunk into our tool-call log and final answer."""
    for delta in update.values():
        if not isinstance(delta, dict):
            continue
        messages = delta.get("messages") or []
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        for msg in messages:
            kind = getattr(msg, "type", "")
            if kind == "ai":
                calls = getattr(msg, "tool_calls", None) or []
                for call in calls:
                    events.append({
                        "id": call.get("id"), "name": call.get("name", "tool"),
                        "args": call.get("args") or {}, "status": "running",
                        "result": "", "t0": time.time(), "seconds": 0.0,
                    })
                if not calls:
                    text = message_text(msg)
                    if text:
                        out["final"] = text
            elif kind == "tool":
                call_id = getattr(msg, "tool_call_id", None)
                event = next((e for e in events if e["id"] == call_id), None)
                if event is None:
                    event = {
                        "id": call_id, "name": getattr(msg, "name", None) or "tool",
                        "args": {}, "status": "running", "result": "",
                        "t0": time.time(), "seconds": 0.0,
                    }
                    events.append(event)
                result = message_text(msg)
                failed = getattr(msg, "status", None) == "error" or result.lower().startswith("error")
                event.update(
                    status="error" if failed else "done",
                    result=result,
                    seconds=time.time() - event["t0"],
                )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_masthead(compact: bool) -> None:
    now = datetime.now()
    dateline = f"{now:%A}, {now.day} {now:%B}"
    st.markdown(
        f'<div class="masthead{" compact" if compact else ""}">'
        f'<div class="dateline">{dateline}</div>'
        '<h1 class="mast-title">Weather and news for any city</h1>'
        '<p class="mast-sub">Ask about one city or compare a few. Answers use live data, '
        'and you can see exactly what the assistant looked up.</p></div>',
        unsafe_allow_html=True,
    )


def render_history() -> None:
    for m in st.session_state.messages:
        avatar = USER_AVATAR if m["role"] == "user" else ASSISTANT_AVATAR
        with st.chat_message(m["role"], avatar=avatar):
            if m.get("tools"):
                failed = any(e["status"] == "error" for e in m["tools"])
                with st.status(
                    summary_label(m["tools"], m.get("elapsed", 0.0)),
                    state="error" if failed else "complete",
                    expanded=False,
                ):
                    st.markdown(log_html(m["tools"]), unsafe_allow_html=True)
            if m.get("error"):
                st.error(m["content"], icon=":material/error:")
                if m.get("detail"):
                    st.caption(m["detail"])
            else:
                st.markdown(m["content"])


def run_turn(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        status_slot = st.empty()
        wait = st.empty()
        answer = st.empty()
        wait.markdown(
            '<div class="log-wait"><span class="dot run"></span>Thinking</div>',
            unsafe_allow_html=True,
        )

        events: list = []
        out = {"final": ""}
        status = None
        log = None
        started = time.time()

        try:
            stream = agent.stream(
                {"messages": model_history()},
                {"recursion_limit": 15},
                stream_mode="updates",
            )
            for update in stream:
                consume_update(update, events, out)
                if events:
                    if status is None:
                        wait.empty()
                        status = status_slot.container().status(live_label(events), expanded=True)
                        log = status.empty()
                    log.markdown(log_html(events), unsafe_allow_html=True)
                    status.update(label=live_label(events), state="running", expanded=True)
        except Exception as exc:
            wait.empty()
            message = explain_error(exc)
            detail = f"{type(exc).__name__}: {str(exc)[:300]}"
            if status is not None:
                status.update(label="Stopped by an error", state="error", expanded=False)
            answer.error(message, icon=":material/error:")
            st.caption(detail)
            st.session_state.messages.append({
                "role": "assistant", "content": message, "error": True, "detail": detail,
                "tools": events, "elapsed": time.time() - started,
            })
            return

        wait.empty()
        elapsed = time.time() - started
        final = out["final"] or "The assistant finished without a reply. Try asking again."
        if status is not None:
            failed = any(e["status"] == "error" for e in events)
            status.update(
                label=summary_label(events, elapsed),
                state="error" if failed else "complete",
                expanded=False,
            )
        answer.markdown(final)
        st.session_state.messages.append({
            "role": "assistant", "content": final, "tools": events, "elapsed": elapsed,
        })


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

typed = st.chat_input("Ask about weather, news, or both for any city")
prompt = st.session_state.pending or typed
st.session_state.pending = None

started_chat = bool(st.session_state.messages) or bool(prompt)
render_masthead(compact=started_chat)

if load_error is not None:
    st.error(
        "The agent could not start. Save your agent code as `agent.py` next to `app.py` "
        "(it must define a variable named `agent`), and check your API keys in `.env`.",
        icon=":material/error:",
    )
    st.caption(f"{type(load_error).__name__}: {load_error}")
    st.stop()

if not started_chat:
    st.markdown('<div class="list-label">Try asking</div>', unsafe_allow_html=True)
    with st.container(key="suggestions"):
        for i, text in enumerate(SUGGESTIONS):
            st.button(text, key=f"sug_{i}", on_click=queue_prompt, args=(text,))

render_history()

if prompt:
    run_turn(prompt)
