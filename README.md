# 🎧 Sales Call Copilot

Turn raw sales-call transcripts into answers and summaries using retrieval-augmented generation (RAG) with a local ChromaDB. Works fully offline for retrieval, and optionally calls **Groq** for LLM-generated answers/summaries.

<p align="center">
  <a href="https://python.org"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue.svg"></a>
  <a href="https://github.com/astral-sh/uv"><img alt="uv" src="https://img.shields.io/badge/uv-Recommended-6f42c1"></a>
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green.svg">
  <img alt="Tests" src="https://img.shields.io/badge/Tests-Pytest%20ready-brightgreen">
</p>

---

## ✨ What you get

- 🔎 **Semantic search** over your transcripts (local embeddings, no external calls required)
- 🧩 **Chunking** that respects conversation flow
- 🏷️ **Heuristic flags** (`mentions_pricing`, `mentions_security`, `mentions_competitor`)
- 🤖 **Optional LLM** answers & summaries via **Groq** (falls back to “top snippets” if no key)
- 🛠️ Clean **Typer** CLI: `ingest`, `list`, `ask`, `summarize`
- ✅ **Pytest** smoke tests

---


## Worklow diagrams

Ingestion Pipeline
<img width="1577" height="1131" alt="image" src="https://github.com/user-attachments/assets/393ade1e-f3c3-4d11-a2ab-8454049ff7f6" />

QA workflow
<img width="1449" height="1042" alt="image" src="https://github.com/user-attachments/assets/e4953458-e8d3-44ff-9baa-5c7443e66220" />

Summarize workflow
<img width="2176" height="711" alt="image" src="https://github.com/user-attachments/assets/456fadd5-53a3-41d0-8be6-686c28174c7e" />




## 📦 Project structure

.
├─ main.py
├─ config.py
├─ utils/
│ ├─ ingestion.py
│ ├─ embeddings.py
│ ├─ retrieval.py
│ └─ prompts.py
├─ transcripts/
│ ├─ 1_demo_call.txt
│ ├─ 2_pricing_call.txt
│ ├─ 3_objection_call.txt
│ └─ 4_negotiation_call.txt
├─ tests/
│ └─ test_pipeline.py
├─ .env # (optional) GROQ_API_KEY=...
├─ .chroma/ # auto-created local vector DB
└─ requirements.txt

yaml
Copy code

---

## ⚡ Quick start

### 1) Install dependencies
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
2) (Optional) Configure Groq
Create a .env in the repo root:

bash
Copy code
# .env
GROQ_API_KEY=your_groq_key_here
No key? No problem. You’ll still get the top retrieved snippets; LLM steps are skipped gracefully.

3) Add transcripts
Put your .txt files into transcripts/. Example files are already listed above.

🧪 Commands
Show help:

bash
Copy code
uv run python main.py --help
Ingest transcripts → build the vector DB
bash
Copy code
uv run python main.py ingest
Sample output:

yaml
Copy code
Ingested 1_demo_call.txt: 60 segments → 6 chunks
Ingested 2_pricing_call.txt: 51 segments → 6 chunks
Ingested 3_objection_call.txt: 60 segments → 4 chunks
Ingested 4_negotiation_call.txt: 85 segments → 6 chunks
Done. Upserted 22 chunks from 4 file(s).
List what’s indexed
bash
Copy code
uv run python main.py list
Output:

diff
Copy code
call_ids:
- 1_demo_call
- 2_pricing_call
- 3_objection_call
- 4_negotiation_call
Ask questions (RAG)
General:

bash
Copy code
uv run python main.py ask "What did security/legal ask us to provide?"
Filter to a single call:

bash
Copy code
uv run python main.py ask "What did security/legal ask us to provide?" --call-id 3_objection_call
Only pricing-related:

bash
Copy code
uv run python main.py ask "Give negative comments when pricing was mentioned" --pricing-only
Tune top-K:

bash
Copy code
uv run python main.py ask "Any actions or next steps?" -k 8
Summarize a call
bash
Copy code
# specific call
uv run python main.py summarize --call-id 1_demo_call

# most recently modified transcript file
uv run python main.py summarize --last
🧠 How it works (short)
Parse → Segment
Each transcript line becomes a Segment(timestamp, speaker, text, flags).

Chunk
Segments are grouped into overlapping windows to preserve chronology and context.

Embed & Upsert
Local embeddings are created and pushed into Chroma with per-chunk metadata:

call_id, start_ts, end_ts

rolling flags (e.g., mentions_pricing)

Retrieve
A similarity search pulls top-K chunks. Optional filters become Chroma “where” clauses.

Generate (optional)
If GROQ_API_KEY is set, the app asks Groq for:

Concise answer with citations (ask)

Structured call summary (summarize)
If not, it prints the top snippets so you can still work offline.

🧰 Troubleshooting
ModuleNotFoundError: config
Run your commands from the repo root (where main.py and config.py live).

No such command 'ask'
Make sure you’re invoking main.py in this repo:

bash
Copy code
uv run python main.py --help
Chroma “where” errors
Let the CLI build filters for you via --call-id and --pricing-only. Don’t pass raw JSON.

LLM not responding
Missing or invalid GROQ_API_KEY. The tool will still return retrieved snippets either way.

Corrupted local DB
Delete .chroma/ and re-run:

bash
Copy code
rm -rf .chroma  # Windows: rmdir /s /q .chroma
uv run python main.py ingest
✅ Tests
bash
Copy code
uv run pytest -q
🔧 Configuration
Environment variables (via .env):

Variable	Required	Description
GROQ_API_KEY	No	Enables LLM responses for ask/summarize.

LLM model defaults are configured in utils/prompts.py.
