# main.py
import pathlib
import typer
from rich import print as rprint

from config import TRANSCRIPTS_DIR, PERSIST_DIR, MAX_CHARS
from utils.ingestion import parse_file, chunk_segments
from utils.embeddings import get_collection, upsert_chunks
from utils.retrieval import list_call_ids, search
from utils.prompts import ask_qa, summarize_call

app = typer.Typer(help="Conversational AI Copilot CLI for sales-call transcripts")


# ----------------------------- Ingestion -----------------------------
@app.command()
def ingest():
    """
    Ingest all .txt transcripts from the transcripts/ folder, chunk, and upsert into the vector DB.
    """
    tdir = pathlib.Path(TRANSCRIPTS_DIR)
    if not tdir.exists():
        rprint(f"[red]Missing transcripts directory:[/red] {TRANSCRIPTS_DIR}")
        raise typer.Exit(code=1)

    files = sorted(tdir.glob("*.txt"))
    if not files:
        rprint(f"[yellow]No .txt files found in {TRANSCRIPTS_DIR}[/yellow]")
        raise typer.Exit(code=2)

    coll = get_collection(PERSIST_DIR)

    total_chunks = 0
    total_files = 0
    for fp in files:
        segs = parse_file(str(fp))
        chunks = chunk_segments(segs, max_chars=MAX_CHARS)
        upserted = upsert_chunks(coll, chunks)
        total_chunks += upserted
        total_files += 1
        rprint(f"Ingested [bold]{fp.name}[/bold]: {len(segs)} segments → {upserted} chunks")

    rprint(f"[green]Done.[/green] Upserted [bold]{total_chunks}[/bold] chunks from [bold]{total_files}[/bold] file(s).")


# ----------------------------- Listing -------------------------------
@app.command("list")
def list_calls():
    """
    List all call_ids currently indexed.
    """
    coll = get_collection(PERSIST_DIR)
    ids = list_call_ids(coll)
    if not ids:
        rprint("[yellow]No calls indexed yet. Run: python main.py ingest[/yellow]")
        raise typer.Exit(code=3)

    rprint("[bold]Indexed call IDs:[/bold]")
    for cid in ids:
        rprint(f" • {cid}")


# ----------------------------- Q&A -----------------------------------
@app.command()
def ask(
    q: str,
    call_id: str = "",
    k: int = 6,
    pricing_only: bool = False,
    security_only: bool = False,
    competitor_only: bool = False,
):
    """
    Ask a free-form question over the indexed calls.

    Examples:
      uv run python main.py ask "What did security/legal ask us to provide?"
      uv run python main.py ask "What is list price?" --call-id 2_pricing_call
      uv run python main.py ask "Security concerns?" --security-only
      uv run python main.py ask "Which competitors came up?" --competitor-only
      uv run python main.py ask "Pricing objections" --pricing-only --call-id 4_negotiation_call
    """
    coll = get_collection(PERSIST_DIR)

    where: dict[str, object] = {}
    if call_id:
        where["call_id"] = call_id
    if pricing_only:
        where["mentions_pricing"] = True
    if security_only:
        where["mentions_security"] = True
    if competitor_only:
        where["mentions_competitor"] = True

    hits = search(coll, q, k=k, where=where)
    if not hits:
        rprint("[yellow]No matches found. Try increasing --k or removing filters.[/yellow]")
        raise typer.Exit(code=4)

    answer = ask_qa(q, hits)
    print(answer)


# ----------------------------- Summarize ------------------------------
@app.command()
def summarize(
    call_id: str = typer.Option("", help="Call ID to summarize (e.g. 4_negotiation_call)"),
    last: bool = typer.Option(False, help="Summarize the most recently modified transcript"),
    k: int = typer.Option(12, help="Number of chunks to retrieve for the summary"),
):
    """
    Summarize a specific call by ID, or the most recent transcript with --last.
    """
    # Resolve --last -> call_id
    if last and not call_id:
        files = sorted(
            pathlib.Path(TRANSCRIPTS_DIR).glob("*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            rprint("[red]No transcripts found. Add files to the 'transcripts/' folder.[/red]")
            raise typer.Exit(code=5)
        call_id = files[0].stem.replace(" ", "_")

    if not call_id:
        rprint("[yellow]Provide --call-id <id> or use --last[/yellow]")
        raise typer.Exit(code=6)

    coll = get_collection(PERSIST_DIR)
    hits = search(coll, f"summary of {call_id}", k=k, where={"call_id": call_id})
    if not hits:
        rprint(f"[yellow]No chunks found for call_id '{call_id}'.[/yellow]")
        raise typer.Exit(code=7)

    print(summarize_call(call_id, hits))


# ----------------------------- Entrypoint -----------------------------
if __name__ == "__main__":
    app()
