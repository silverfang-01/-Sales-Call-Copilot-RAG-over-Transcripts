import re, uuid, pathlib
from dataclasses import dataclass

# Matches: [MM:SS] Speaker: text...
LINE_RE = re.compile(r"^\[(?P<ts>\d{2}:\d{2})\]\s*(?P<speaker>[^:]+):\s*(?P<text>.+)$")

# Light keyword flags you can filter on later
PRICING_RE   = re.compile(r"(₹|\bprice|pricing|discount|overage|minute|SKU|TCV|ARR|seat)", re.I)
SECURITY_RE  = re.compile(r"(SOC|ISO|pen-?test|DPA|GDPR|DPDPA|KMS|encrypt|SSO|SAML|OIDC|SCIM|retention)", re.I)
COMP_RE      = re.compile(r"(Competitor\s+[A-Z]|Brightcall|battle-?card)", re.I)

@dataclass
class Segment:
    id: str
    call_id: str
    idx: int
    timestamp: str
    speaker: str
    text: str
    flags: dict

def _flags_for(t: str) -> dict:
    return {
        "mentions_pricing":    bool(PRICING_RE.search(t)),
        "mentions_security":   bool(SECURITY_RE.search(t)),
        "mentions_competitor": bool(COMP_RE.search(t)),
    }

def parse_file(path: str) -> list[Segment]:
    """Parse a transcript .txt into structured segments."""
    call_id = pathlib.Path(path).stem.replace(" ", "_")
    segs, i = [], 0
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            ln = raw.strip()
            if not ln:
                continue
            m = LINE_RE.match(ln)
            if not m:
                continue
            segs.append(Segment(
                id=str(uuid.uuid4()),
                call_id=call_id,
                idx=i,
                timestamp=m["ts"].strip(),
                speaker=m["speaker"].strip(),
                text=m["text"].strip(),
                flags=_flags_for(m["text"])
            ))
            i += 1
    return segs

def chunk_segments(segs: list[Segment], max_chars: int = 1500) -> list[dict]:
    """
    Coalesce adjacent segments into ~max_chars chunks.
    Returns a list of {id, text, meta} dicts ready for the vector DB.
    Note: Chroma metadata values must be scalar (str/int/float/bool/None).
    """
    chunks, buf, metas, size = [], [], [], 0

    def flush():
        nonlocal buf, metas, size
        if not buf:
            return
        # IMPORTANT: metadata only has scalar values (no lists)
        chunks.append({
            "id": str(uuid.uuid4()),
            "text": "\n".join(buf),
            "meta": {
                "call_id": metas[0].call_id,
                "start_ts": metas[0].timestamp,
                "end_ts": metas[-1].timestamp,
                "seg_start_idx": metas[0].idx,   # int (OK for Chroma)
                "seg_end_idx": metas[-1].idx,    # int (OK for Chroma)
                "mentions_pricing":    any(m.flags["mentions_pricing"] for m in metas),
                "mentions_security":   any(m.flags["mentions_security"] for m in metas),
                "mentions_competitor": any(m.flags["mentions_competitor"] for m in metas),
            }
        })
        buf.clear(); metas.clear(); size = 0

    for s in segs:
        piece = f"[{s.timestamp}] {s.speaker}: {s.text}"
        if size and size + len(piece) > max_chars:
            flush()
        buf.append(piece)
        metas.append(s)
        size += len(piece)

    flush()
    return chunks
