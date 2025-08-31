# 🎧 Sales Call Copilot

Turn raw sales-call transcripts into **answers** and **summaries** with Retrieval-Augmented Generation (RAG) on a **local ChromaDB** index.  
Works fully **offline** for search/retrieval; optionally uses **Groq** (OpenAI-compatible) for LLM outputs.

---

## ✨ Features

- 🔎 **Semantic search** over transcripts (local sentence-transformer embeddings; no external calls required)
- 🧩 **Character-budget chunking** that preserves conversation flow + timestamps
- 🏷️ Heuristic flags in metadata: `mentions_pricing`, `mentions_security`, `mentions_competitor`
- 🤖 **Optional** LLM answers & summaries via Groq (gracefully falls back to **top snippets** if no key)
- 🛠️ Clean **Typer** CLI: `ingest`, `list`, `ask`, `summarize`
- 📎 Deterministic **Sources** section appended to every answer/summary for traceability

---

## 🗂 Project Structure

.
├─ main.py # Typer CLI (ingest/list/ask/summarize)
├─ config.py # TRANSCRIPTS_DIR, PERSIST_DIR, MAX_CHARS, GROQ_*
├─ utils/
│ ├─ ingestion.py # parse_file, chunk_segments
│ ├─ embeddings.py # get_collection, upsert_chunks
│ ├─ retrieval.py # list_call_ids, _to_chroma_where, search
│ └─ prompts.py # ask_qa, summarize_call, sources formatter
├─ transcripts/ # your .txt transcripts (samples welcome)
├─ .chroma/ # auto-created local vector DB (on first ingest)
├─ .env # (optional) GROQ_API_KEY=..., GROQ_MODEL=...
└─ requirements.txt

yaml
Copy code

---

## Workflow diagrams

Ingestion pipeline
<img width="1577" height="1131" alt="image" src="https://github.com/user-attachments/assets/0f0a02cf-f86f-41c5-827c-066f960df380" />

Q&A Flow
<img width="1449" height="1042" alt="image" src="https://github.com/user-attachments/assets/f1d77fd2-a46e-4121-86e9-8e33a712dac8" />

Summarization Flow
<img width="2176" height="711" alt="image" src="https://github.com/user-attachments/assets/26283e6d-550a-4321-9b5d-435c897ebd97" />




## ⚡ Quick Start

**Prereqs:** Python **3.10+** recommended.

### 1) Create a virtualenv & install deps

Using **uv** (recommended):
```bash
uv venv
uv pip install -r requirements.txt
Or with pip:

bash
Copy code
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
2) (Optional) Configure Groq for LLM outputs
Create a .env in the repo root:

bash
Copy code
# .env
GROQ_API_KEY=your_groq_key_here
# Optional (falls back to a sensible default if omitted):
# GROQ_MODEL=llama3-8b-8192
No key? No problem. Retrieval still works offline. You’ll get the top retrieved snippets instead of an LLM-generated answer/summary.

3) Add transcripts
Drop your .txt files into transcripts/. (You can start with your own or sample files.)

🧪 CLI Commands
Show help:

bash
Copy code
uv run python main.py --help
Ingest transcripts → build/update the local vector DB:

bash
Copy code
uv run python main.py ingest
Example output:

yaml
Copy code
Ingested 1_demo_call.txt: 60 segments → 6 chunks
Ingested 2_pricing_call.txt: 51 segments → 6 chunks
Ingested 3_objection_call.txt: 60 segments → 4 chunks
Ingested 4_negotiation_call.txt: 85 segments → 6 chunks
Done. Upserted 22 chunks from 4 file(s).
List what’s indexed:

bash
Copy code
uv run python main.py list
Ask questions (RAG):

bash
Copy code
# general
uv run python main.py ask "What did security/legal ask us to provide?"

# single call only
uv run python main.py ask "What did security/legal ask us to provide?" --call-id 3_objection_call

# pricing-only
uv run python main.py ask "Where was pricing discussed?" --pricing-only

# security-only
uv run python main.py ask "Any security concerns?" --security-only

# competitor-only
uv run python main.py ask "Which competitors came up?" --competitor-only

# tune top-K retrieval
uv run python main.py ask "Any next steps?" --k 8
Summarize a call:

bash
Copy code
# specific call
uv run python main.py summarize --call-id 1_demo_call

# most recently modified transcript file
uv run python main.py summarize --last
Exit codes: ingest (1: missing dir, 2: no files), list (3: empty index),
ask (4: no hits), summarize (5/6/7: no transcripts / no call_id / no chunks).

🧠 How It Works
1) Parse → Segment
Each transcript line becomes a Segment(timestamp, speaker, text, idx, call_id, flags).

2) Chunk
Segments are coalesced into ~MAX_CHARS chunks (character budget) while preserving chronology. Each chunk stores scalar metadata for Chroma:

call_id, start_ts, end_ts

seg_start_idx, seg_end_idx

mentions_pricing, mentions_security, mentions_competitor (booleans via any(...))

3) Embed & Upsert (ChromaDB)
get_collection() creates a persistent collection with DefaultEmbeddingFunction (local sentence-transformers).
On upsert, embeddings are computed at write time and stored with metadata in an HNSW index (hnsw:space="cosine").

4) Retrieve
search() runs a vector query for top-K with optional metadata where filters.
Multi-key filters are normalized to explicit $and; operator filters like $or pass through.
If a filtered query for a specific call_id returns zero, a fallback re-queries unfiltered and client-filters by call_id to avoid empty results.

5) Generate (optional)
If GROQ_API_KEY is set, we call Groq for:

Q&A: concise answer grounded in snippets

Summary: structured Markdown (TL;DR, Agenda, Key Moments, Objections, Pricing, Security, Competitors, Action Items, Risks)

We do not add inline citations. Instead, we append a deterministic Sources block built from the retrieval hits:

php-template
Copy code
Sources:
[1] <call_id>  <start_ts>–<end_ts>  —  <shortened snippet>
...
If no key or an LLM error occurs, you still get a clear message plus the top snippets so the tool remains useful offline.

🧩 Design Decisions (for reviewers)
Low-level design: separate modules by lifecycle (ingestion ↔ embeddings/storage ↔ retrieval ↔ prompting ↔ CLI). Functions are small and typed; metadata remains scalar for Chroma.

Storage design: one record per chunk (document + metadata + vector). HNSW + cosine suits text embeddings; metadata filters shrink the candidate set server-side.

Prompt engineering: strict, low-temperature prompts that only use retrieved snippets; no inline citations. We append deterministic Sources for auditability.

GenAI skills / RAG: local embeddings on upsert, metadata-aware retrieval with a call_id fallback, compact result shaping (score = 1 − distance), and clear degradation when LLM is unavailable.

🛟 Troubleshooting
ModuleNotFoundError: config — run commands from the repo root (where main.py and config.py live).

No such command 'ask' — check CLI help:

bash
Copy code
uv run python main.py --help
Chroma “where” errors — use CLI flags (--call-id, --pricing-only, etc.); don’t pass raw JSON.

LLM not responding — missing/invalid GROQ_API_KEY. Retrieval still works; you’ll see top snippets + Sources.

Corrupted local DB — reset and re-ingest:

bash
Copy code
rm -rf .chroma   # Windows: rmdir /s /q .chroma
uv run python main.py ingest
✅ Tests
If you include tests, run them with:

bash
Copy code
uv run pytest -q
