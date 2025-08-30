# utils/prompts.py
from typing import List, Dict
import sys
from openai import OpenAI
from config import GROQ_API_KEY, GROQ_MODEL
from textwrap import shorten

# System prompt for call summarization
SYS_SUMMARY = """
You are a precise meeting summarizer for sales calls. You MUST use only the provided Snippets as ground truth.
Do not invent, infer, or bring in outside knowledge. If something is not present in the snippets, write “Unknown”.

Output Markdown with these sections in this exact order and casing (no extra sections):
TL;DR
Agenda / Topics
Key Moments
Objections & Responses
Pricing
Security
Competitors
Action Items
Risks / Open Questions

Formatting & style rules:
- TL;DR: 3–5 short bullets.
- Use compact bullets elsewhere; one idea per bullet.
- Prefer present tense and plain, un-hyped language.
- Include timestamps like [mm:ss] when available in snippets.
- Use role labels from snippets (e.g., AE, SE, Prospect, or names if shown).
- If a section has nothing in the snippets, write “None mentioned.” (not omitted).
- Do NOT add citations in the body; they’ll be appended by the caller.
"""
# ---- Groq-only client (OpenAI-compatible) ----
if not GROQ_API_KEY:
    # Hard fail with a clear message so you know what's wrong
    print("ERROR: GROQ_API_KEY not found. Create a .env with GROQ_API_KEY=gsk-... ", file=sys.stderr)
    client = None
    DEFAULT_MODEL = None
else:
    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    DEFAULT_MODEL = GROQ_MODEL or "llama3-8b-8192"

# -------------------- prompt templates --------------------
SYS_QA = """You are a sales-call analysis copilot.
Answer ONLY using the provided call snippets.
After each factual claim, include bracketed citations like [call_id start_ts–end_ts].
If the context is insufficient, say so briefly.
Keep answers concise (3–6 sentences), neutral, and precise.
"""

SYS_SUM = """Summarize the call for a sales rep. Include:
- Participants & roles (if available)
- Key themes and objections
- Pricing discussion (if any)
- Security/compliance asks (if any)
- Next steps & owners
Add citations like [call_id start_ts–end_ts]. Keep to 5–8 bullets.
"""

def _format_snips(hits: List[Dict]) -> str:
    blocks = []
    for h in hits:
        m = h["meta"]
        cid = m.get("call_id", "?"); s = m.get("start_ts", "?"); e = m.get("end_ts", "?")
        blocks.append(f"[{cid} {s}–{e}]\n{h['text']}")
    return "\n\n---\n\n".join(blocks)

def ask_qa(question: str, hits: List[Dict]) -> str:
    ctx = _format_snips(hits) if hits else "(no relevant snippets retrieved)"

    # If Groq isn't configured, still show a Sources section built from hits
    if not client or not DEFAULT_MODEL:
        return _format_answer_with_sources(
            "(GROQ not configured) Showing top snippets-derived context below.",
            hits
        )

    msgs = [
        {"role": "system", "content": SYS_QA},
        {
            "role": "user",
            "content": (
                "You must answer ONLY using the snippets below.\n"
                "If the answer is not present in the snippets, say you don't know.\n"
                "Answer concisely (1–6 sentences). Do NOT include citations or a 'Sources' section.\n\n"
                f"Question: {question}\n\nSnippets:\n{ctx}"
            ),
        },
    ]

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=msgs,
            temperature=0.2,
        )
        answer = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        # Graceful fallback if the LLM call fails
        answer = f"(LLM error: {e.__class__.__name__}) Using retrieved snippets only."

    # Append compact, deterministic sources from the actual hits
    return _format_answer_with_sources(answer, hits)

def summarize_call(call_id: str, hits: List[Dict]) -> str:
    """
    Build a concise, structured summary for a single call using ONLY the retrieved snippets.
    Always append a deterministic Sources block based on hits.
    """
    ctx = _format_snips(hits) if hits else "(no relevant snippets retrieved)"

    # Fallback if Groq isn't configured
    if not client or not DEFAULT_MODEL:
        return _format_answer_with_sources(
            f"(GROQ not configured) Top snippets for {call_id}:\n\n{ctx}\n",
            hits
        )

    msgs = [
        {"role": "system", "content": SYS_SUMMARY},
        {
            "role": "user",
            "content": (
                "You must summarize ONLY using the snippets below.\n"
                "If a detail isn't present, say you don't know.\n"
                "Output the following sections, concise, no citations:\n"
                "TL;DR (3–5 bullets)\n"
                "Agenda / Topics\n"
                "Key Moments (use timestamps if present)\n"
                "Objections & Responses\n"
                "Pricing\n"
                "Security\n"
                "Competitors\n"
                "Action Items (who/what/when)\n"
                "Risks / Open Questions\n\n"
                f"Call ID: {call_id}\n\nSnippets:\n{ctx}"
            ),
        },
    ]

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=msgs,
            temperature=0.2,
        )
        answer = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        answer = f"(LLM error: {e.__class__.__name__}) Showing retrieved snippets only.\n\n{ctx}"

    return _format_answer_with_sources(answer, hits)

def _format_answer_with_sources(answer: str, hits: list[dict], max_sources: int = 5, max_snippet_chars: int = 160) -> str:
    """
    Takes the raw LLM answer and appends a compact Sources section built from the retrieved hits.
    Each source shows: [#] call_id start–end : short snippet
    """
    if not hits:
        return answer.strip()

    lines = []
    used = 0
    for i, h in enumerate(hits, start=1):
        meta = (h.get("meta") or {})
        call_id = str(meta.get("call_id", "unknown_call"))
        start_ts = str(meta.get("start_ts", "?"))
        end_ts   = str(meta.get("end_ts", "?"))
        snippet = shorten((h.get("text") or "").replace("\n", " "), width=max_snippet_chars, placeholder="…")
        lines.append(f"[{i}] {call_id}  {start_ts}–{end_ts}  —  {snippet}")
        used += 1
        if used >= max_sources:
            break

    return (
        answer.strip()
        + "\n\n"
        + "Sources:\n"
        + "\n".join(lines)
    )