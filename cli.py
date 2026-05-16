#!/usr/bin/env python3
"""
cli.py – Command-line interface for MCP Context Assistant
Usage:
  python cli.py ingest ./knowledge_base
  python cli.py ask "What is the time off policy?"
  python cli.py search "incident response"
  python cli.py stats
  python cli.py list
"""
import sys
import asyncio
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def cmd_ingest(args):
    from api.ingestion import bulk_ingest_directory, ingest_file
    path = Path(args.path)
    if path.is_dir():
        console.print(f"[bold cyan]Indexing directory:[/] {path}")
        results = bulk_ingest_directory(path)
    elif path.is_file():
        console.print(f"[bold cyan]Indexing file:[/] {path}")
        results = [ingest_file(path)]
    else:
        console.print(f"[red]Path not found:[/] {path}")
        return

    table = Table(title="Ingestion Results")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Chunks", justify="right")
    table.add_column("Sections", justify="right")

    for r in results:
        status_color = "green" if r.get("status") == "indexed" else "red"
        table.add_row(
            r.get("filename", "?"),
            f"[{status_color}]{r.get('status', '?')}[/]",
            str(r.get("chunks", 0)),
            str(r.get("sections", 0)),
        )
    console.print(table)


def cmd_search(args):
    from api.retrieval import get_orchestrator
    orch = get_orchestrator()
    console.print(f"\n[bold]Query:[/] {args.query}\n")
    result = orch.retrieve(args.query, top_k=args.top_k)

    if result["status"] == "blocked":
        console.print(f"[red]Blocked:[/] {result['reason']}")
        return

    hits = result["hits"]
    console.print(f"[green]Found {len(hits)} results[/]\n")

    for i, hit in enumerate(hits, 1):
        meta = hit["metadata"]
        score_color = "green" if hit["score"] > 0.7 else "yellow" if hit["score"] > 0.4 else "red"
        panel = Panel(
            hit["text"][:400] + ("…" if len(hit["text"]) > 400 else ""),
            title=f"[bold]{i}. {meta.get('source','?')}[/] | [{score_color}]{hit['score']:.2%}[/] | §{meta.get('section','')}",
            border_style="dim",
        )
        console.print(panel)


def cmd_ask(args):
    from api.qa_engine import get_qa_engine

    async def run():
        engine = get_qa_engine()
        console.print(f"\n[bold cyan]Question:[/] {args.question}\n")
        with console.status("[bold green]Retrieving context & generating answer…"):
            result = await engine.answer(
                query=args.question,
                top_k=args.top_k,
                use_memory=False,
            )
        console.print(Panel(
            Markdown(result["answer"]),
            title="[bold green]Answer[/]",
            border_style="green",
        ))
        if result["sources"]:
            console.print(f"[dim]Sources: {', '.join(result['sources'])}[/]")
        console.print(f"[dim]Chunks used: {result['hit_count']} | Tokens: ~{result['token_estimate']}[/]")

    asyncio.run(run())


def cmd_stats(args):
    from api.vector_store import get_vector_store
    from config import get_settings
    store = get_vector_store()
    s = get_settings()

    table = Table(title="MCP Assistant Stats")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Chunks", str(store.count()))
    table.add_row("Documents", str(len(store.list_sources())))
    table.add_row("LLM Provider", s.llm_provider)
    table.add_row("LLM Model", s.llm_model)
    table.add_row("Embedding Model", s.embedding_model)
    table.add_row("Top-K", str(s.top_k_results))
    table.add_row("Max Context Tokens", str(s.max_context_tokens))
    table.add_row("Similarity Threshold", str(s.similarity_threshold))

    console.print(table)


def cmd_list(args):
    from api.vector_store import get_vector_store
    store = get_vector_store()
    sources = store.list_sources()

    if not sources:
        console.print("[yellow]No documents indexed yet.[/]")
        return

    table = Table(title=f"Indexed Documents ({len(sources)})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Filename", style="cyan")

    for i, src in enumerate(sources, 1):
        table.add_row(str(i), src)

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="MCP Context Assistant CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py ingest ./knowledge_base
  python cli.py ingest ./my_doc.md
  python cli.py search "time off policy" --top-k 3
  python cli.py ask "What is the engineering on-call process?"
  python cli.py stats
  python cli.py list
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # ingest
    p_ingest = sub.add_parser("ingest", help="Index markdown documents")
    p_ingest.add_argument("path", help="File or directory path")

    # search
    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query")
    p_search.add_argument("--top-k", type=int, default=5, dest="top_k")

    # ask
    p_ask = sub.add_parser("ask", help="Ask a question")
    p_ask.add_argument("question")
    p_ask.add_argument("--top-k", type=int, default=5, dest="top_k")

    # stats
    sub.add_parser("stats", help="Show index statistics")

    # list
    sub.add_parser("list", help="List indexed documents")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    dispatch = {
        "ingest": cmd_ingest,
        "search": cmd_search,
        "ask": cmd_ask,
        "stats": cmd_stats,
        "list": cmd_list,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
