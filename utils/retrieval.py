# utils/retrieval.py
from typing import Any, Dict, List

def list_call_ids(coll) -> List[str]:
    data = coll.get(include=["metadatas"])
    metas = data.get("metadatas") or []
    call_ids = {m.get("call_id") for m in metas if isinstance(m, dict) and m.get("call_id")}
    return sorted(call_ids)

def _to_chroma_where(where: Dict[str, Any] | None):
    """
    Normalize filters for Chroma.
    - None/{} -> None
    - {"a":1} -> {"a":1}
    - {"a":1,"b":2} -> {"$and":[{"a":1},{"b":2}]}
    - If already has a $-operator, pass through.
    """
    if not where:
        return None
    if any(str(k).startswith("$") for k in where):
        return where
    if len(where) == 1:
        k, v = next(iter(where.items()))
        return {k: v}
    return {"$and": [{k: v} for k, v in where.items()]}

def _to_hits(res) -> List[Dict[str, Any]]:
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    # score = 1 - distance (when available)
    hits: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(docs, metas, dists):
        try:
            score = 1.0 - float(dist)
        except Exception:
            score = None
        hits.append({"id": None, "text": doc, "meta": meta, "score": score})
    return hits

def search(coll, q: str, k: int = 6, where: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """
    Return flat hits: [{'id': ..., 'text': ..., 'meta': {...}, 'score': float}, ...]
    Tries a filtered query first; if it yields 0, falls back to unfiltered and
    filters in Python (handles Chroma filter quirks).
    """
    include = ["documents", "metadatas", "distances"]
    chroma_where = _to_chroma_where(where)

    # 1) try with filter (if any)
    res = coll.query(query_texts=[q], n_results=k, where=chroma_where, include=include)
    hits = _to_hits(res)

    # 2) fallback: if asked for a specific call_id and nothing came back, query
    #    without a filter and then filter in Python.
    if (not hits) and where and isinstance(where, dict) and "call_id" in where:
        unfiltered = coll.query(query_texts=[q], n_results=max(k, 12), include=include)
        uf_hits = _to_hits(unfiltered)
        call_id = where["call_id"]
        hits = [h for h in uf_hits if isinstance(h.get("meta"), dict) and h["meta"].get("call_id") == call_id]
        hits = hits[:k]

    return hits
