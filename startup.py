#!/usr/bin/env python3
"""
startup.py – Bootstrap script for first-time setup.
Run once before starting the server to verify environment and pre-load docs.

Usage: python startup.py
"""
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def check_python():
    if sys.version_info < (3, 9):
        console.print("[red]❌ Python 3.9+ required[/]")
        sys.exit(1)
    console.print(f"[green]✓[/] Python {sys.version_info.major}.{sys.version_info.minor}")


def check_env():
    env_path = Path(".env")
    example_path = Path(".env.example")

    if not env_path.exists():
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            console.print("[yellow]⚠[/]  Created .env from .env.example — please edit it")
        else:
            console.print("[red]❌ .env file not found[/]")
    else:
        console.print("[green]✓[/] .env file found")

    # Load and check key settings
    from dotenv import load_dotenv
    load_dotenv()

    provider = os.getenv("LLM_PROVIDER", "anthropic")
    model = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    embedding = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("LLM Provider", f"[cyan]{provider}[/]")
    table.add_row("LLM Model", f"[cyan]{model}[/]")
    table.add_row("Anthropic Key", "[green]set[/]" if api_key and not api_key.startswith("your_") else "[yellow]not set (using mock/ollama)[/]")
    table.add_row("Embedding Model", f"[cyan]{embedding}[/]")
    console.print(table)

    return provider, api_key


def check_directories():
    dirs = ["knowledge_base", "sample_docs", "memory", "context", "logs", "vector_store", "prompts"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    console.print(f"[green]✓[/] All directories ready")


def check_dependencies():
    required = ["fastapi", "uvicorn", "chromadb", "pydantic", "loguru", "frontmatter", "tiktoken"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)

    if missing:
        console.print(f"[red]❌ Missing packages: {', '.join(missing)}[/]")
        console.print("Run: [bold]pip install -r requirements.txt[/]")
        sys.exit(1)
    console.print(f"[green]✓[/] Core dependencies installed")

    # Optional
    try:
        from sentence_transformers import SentenceTransformer
        console.print("[green]✓[/] sentence-transformers (semantic embeddings)")
    except ImportError:
        console.print("[yellow]⚠[/]  sentence-transformers not installed — using hash-based fallback embeddings")
        console.print("   Install: [dim]pip install sentence-transformers[/]")


def ingest_samples():
    from api.ingestion import bulk_ingest_directory
    from api.vector_store import get_vector_store

    store = get_vector_store()
    if store.count() > 0:
        console.print(f"[green]✓[/] Vector store already has {store.count()} chunks indexed")
        return

    # Index sample docs
    sample_dir = Path("./sample_docs")
    kb_dir = Path("./knowledge_base")

    total = 0
    for d in [sample_dir, kb_dir]:
        if d.exists() and any(d.glob("*.md")):
            results = bulk_ingest_directory(d)
            indexed = [r for r in results if r.get("status") == "indexed"]
            chunks = sum(r.get("chunks", 0) for r in indexed)
            total += chunks
            console.print(f"[green]✓[/] Indexed {len(indexed)} docs from {d} ({chunks} chunks)")

    if total == 0:
        console.print("[yellow]⚠[/]  No documents found to index. Add .md files to knowledge_base/")


def check_ollama(provider):
    if provider != "ollama":
        return
    import httpx
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        if models:
            console.print(f"[green]✓[/] Ollama running, models: {', '.join(models)}")
        else:
            console.print("[yellow]⚠[/]  Ollama running but no models pulled")
            console.print("   Run: [bold]ollama pull llama3[/]")
    except Exception:
        console.print("[yellow]⚠[/]  Ollama not running. Start with: [bold]ollama serve[/]")
        console.print("   Then pull a model: [bold]ollama pull llama3[/]")


def main():
    console.print(Panel("[bold cyan]MCP Context Assistant — Setup Check[/]", expand=False))
    console.print()

    check_python()
    check_dependencies()
    check_directories()
    provider, api_key = check_env()
    check_ollama(provider)

    console.print()
    console.print("[bold]Initializing vector store and indexing documents…[/]")
    ingest_samples()

    console.print()
    console.print(Panel(
        "[bold green]Setup complete![/]\n\n"
        "Start the server:\n"
        "  [bold]uvicorn main:app --reload --port 8000[/]\n\n"
        "Open in browser:\n"
        "  [bold cyan]http://localhost:8000[/]\n\n"
        "API docs:\n"
        "  [bold cyan]http://localhost:8000/docs[/]",
        title="Ready",
        expand=False,
    ))


if __name__ == "__main__":
    main()
