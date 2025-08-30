import os
import pytest

from config import PERSIST_DIR
from utils.embeddings import get_collection
from utils.retrieval import list_call_ids, search
from utils.prompts import ask_qa, summarize_call

# ----- helpers ---------------------------------------------------------------

def _have_groq_key() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))

# ----- retrieval-only tests (no LLM) ----------------------------------------

def test_call_ids_present():
    coll = get_collection(PERSIST_DIR)
    ids = list_call_ids(coll)
    assert isinstance(ids, list) and len(ids) > 0

def test_search_unfiltered_returns_hits():
    coll = get_collection(PERSIST_DIR)
    hits = search(coll, "security or legal", k=6)
    assert isinstance(hits, list) and len(hits) > 0
    # Each hit must have required fields
    for h in hits:
        assert "text" in h and "meta" in h and "score" in h

def test_search_filtered_by_call_id():
    coll = get_collection(PERSIST_DIR)
    # Pick any valid call_id from the store
    call_ids = list_call_ids(coll)
    target = call_ids[0]
    hits = search(coll, "anything", k=4, where={"call_id": target})
    assert len(hits) > 0
    for h in hits:
        assert h["meta"]["call_id"] == target

def test_search_filtered_pricing_only():
    coll = get_collection(PERSIST_DIR)
    hits = search(coll, "pricing", k=6, where={"mentions_pricing": True})
    # Not guaranteed for every dataset, but demo data should have some
    assert len(hits) > 0
    for h in hits:
        assert h["meta"]["mentions_pricing"] is True

# ----- LLM round-trip tests (skip if no key) --------------------------------

@pytest.mark.skipif(not _have_groq_key(), reason="GROQ_API_KEY not set")
def test_ask_qa_non_empty_answer():
    coll = get_collection(PERSIST_DIR)
    hits = search(coll, "What did security/legal ask us to provide?", k=8)
    assert len(hits) > 0
    ans = ask_qa("What did security/legal ask us to provide?", hits)
    assert isinstance(ans, str) and ans.strip() != ""

@pytest.mark.skipif(not _have_groq_key(), reason="GROQ_API_KEY not set")
def test_summarize_call_non_empty():
    coll = get_collection(PERSIST_DIR)
    call_ids = list_call_ids(coll)
    target = call_ids[0]
    hits = search(coll, f"summary of {target}", k=10, where={"call_id": target})
    txt = summarize_call(target, hits)
    assert isinstance(txt, str) and txt.strip() != ""
