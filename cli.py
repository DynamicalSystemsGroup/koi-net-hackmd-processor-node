import argparse
import asyncio
import logging
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.markdown import Markdown

# Import core components
from hackmd_processor_node import index_db

logger = logging.getLogger(__name__)
DB_PATH = ".koi/index_db/index.db"

# CLI command implementations
async def list_notes_cmd(limit: int = 50, offset: int = 0, search: str | None = None):
    """List all tracked notes."""
    db_path = DB_PATH  # This should be configurable
    notes = index_db.get_notes(db_path, limit=limit, offset=offset, search_term=search)

    if not notes:
        print("No notes are currently indexed." if not search else f"No notes found matching '{search}'.")
        return

    console = Console()
    table = Table(title="Indexed HackMD Notes")
    table.add_column("Note ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Created", style="yellow")
    table.add_column("Last Updated", style="yellow")
    table.add_column("Word Count", style="magenta")
    table.add_column("Tags", style="blue")

    for note in notes:
        # Format timestamps
        created = format_timestamp(note.get("created_at", ""))
        updated = format_timestamp(note.get("last_updated", ""))

        table.add_row(
            note.get("note_id", ""),
            note.get("title", ""),
            created,
            updated,
            str(note.get("word_count", 0)),
            note.get("tags", "")
        )

    console.print(table)
    total = index_db.count_notes(db_path, search)
    console.print(f"Showing {len(notes)} of {total} notes")

async def show_note_cmd(note_id: str):
    """Show details and content of a specific note."""
    db_path = DB_PATH
    note = index_db.get_note_by_id(db_path, note_id)

    if not note:
        print(f"Note not found: {note_id}")
        return

    console = Console()

    # Create layout
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main")
    )

    # Set header
    layout["header"].update(
        Panel(
            Text(f"Note: {note['title']}", style="bold white"),
            style="bold white on blue"
        )
    )

    # Create detail panel with metadata
    details = [
        f"**Note ID:** {note['note_id']}\n",
        f"**Created:** {format_timestamp(note['created_at'])}\n",
        f"**Last Updated:** {format_timestamp(note['last_updated'])}\n",
        f"**Word Count:** {note.get('word_count', 0)}\n",
    ]

    if note.get("tags"):
        details.append(f"**Tags:** {note['tags']}\n")

    details.append("\n---\n\n")

    # Add content
    details.append(note.get("content", ""))

    layout["main"].update(Panel(Markdown("\n".join(details))))

    console.print(layout)

async def show_history_cmd(note_id: str, limit: int = 20):
    """Show history for a specific note."""
    db_path = DB_PATH

    # First get note to verify existence and get RID
    note = index_db.get_note_by_id(db_path, note_id)

    if not note:
        print(f"Note not found: {note_id}")
        return

    note_rid = note.get("note_rid")

    if not note_rid:
        print(f"Note {note_id} has no RID, cannot retrieve history.")
        return

    # Get history
    history = index_db.get_note_history(db_path, note_rid, limit)

    if not history:
        print(f"No history found for note: {note_id}")
        return

    console = Console()
    table = Table(title=f"History for Note: {note.get('title', note_id)}")
    table.add_column("Timestamp", style="yellow")
    table.add_column("Event Type", style="cyan")
    table.add_column("Summary", style="green")
    table.add_column("Bundle RID", style="dim")

    for event in history:
        # Format timestamp
        timestamp = format_timestamp(event.get("timestamp", ""))

        table.add_row(
            timestamp,
            event.get("event_type", ""),
            event.get("summary", ""),
            event.get("bundle_rid", "")
        )

    console.print(table)

async def search_notes_cmd(query: str, limit: int = 20):
    """Search notes by content."""
    db_path = DB_PATH
    results = index_db.search_notes_content(db_path, query, limit)

    if not results:
        print(f"No notes found matching '{query}'.")
        return

    console = Console()
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Note ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Last Updated", style="yellow")
    table.add_column("Preview", style="white")

    for note in results:
        # Format timestamp
        updated = format_timestamp(note.get("last_updated", ""))

        table.add_row(
            note.get("note_id", ""),
            note.get("title", ""),
            updated,
            note.get("content_preview", "")
        )

    console.print(table)
    console.print(f"Found {len(results)} notes matching '{query}'")

async def show_stats_cmd():
    """Show statistics about indexed notes."""
    db_path = DB_PATH
    stats = index_db.get_stats(db_path)

    console = Console()

    # Display stats header
    console.print(Panel(Text("HackMD Notes Statistics", style="bold white"), style="bold blue"))

    # Display basic stats
    console.print(f"Total Notes: [cyan]{stats['total_notes']}[/cyan]")
    console.print(f"Total Words: [cyan]{stats['total_words']:,}[/cyan]")
    console.print(f"Average Words per Note: [cyan]{stats['avg_words_per_note']}[/cyan]")

    # Display newest and oldest note info if available
    if stats.get("newest_note"):
        newest = stats["newest_note"]
        console.print(f"Newest Note: [yellow]{newest['title']}[/yellow] (ID: {newest['note_id']}, Updated: {format_timestamp(newest['last_updated'])})")

    if stats.get("oldest_note"):
        oldest = stats["oldest_note"]
        console.print(f"Oldest Note: [yellow]{oldest['title']}[/yellow] (ID: {oldest['note_id']}, Created: {format_timestamp(oldest['created_at'])})")

def format_timestamp(timestamp: str | int) -> str:
    """Format a timestamp string to a readable date."""
    if not timestamp:
        return "N/A"

    try:
        # Handle both string timestamps and integer timestamps
        if isinstance(timestamp, str):
            if timestamp.isdigit():
                # Convert to integer if it's a string of digits
                timestamp = int(timestamp)

        if isinstance(timestamp, int):
            # Convert milliseconds timestamp to datetime
            dt = datetime.datetime.fromtimestamp(timestamp / 1000)
        else:
            # Try to parse ISO format
            dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp)

def main():
    parser = argparse.ArgumentParser(description="KOI-net HackMD Notes Explorer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # CLI commands
    list_parser = subparsers.add_parser("list", help="List all indexed notes")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum number of notes to show")
    list_parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    list_parser.add_argument("--search", type=str, help="Filter notes by search term")

    show_parser = subparsers.add_parser("show", help="Show a specific note")
    show_parser.add_argument("note_id", help="Note ID to display")

    history_parser = subparsers.add_parser("history", help="Show history for a specific note")
    history_parser.add_argument("note_id", help="Note ID to show history for")
    history_parser.add_argument("--limit", type=int, default=20, help="Maximum number of history entries to show")

    search_parser = subparsers.add_parser("search", help="Search notes by content")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=20, help="Maximum number of results to show")

    subparsers.add_parser("stats", help="Show statistics about indexed notes")

    args = parser.parse_args()

    # Handle command execution
    if args.command == "list":
        asyncio.run(list_notes_cmd(args.limit, args.offset, args.search))
    elif args.command == "show":
        asyncio.run(show_note_cmd(args.note_id))
    elif args.command == "history":
        asyncio.run(show_history_cmd(args.note_id, args.limit))
    elif args.command == "search":
        asyncio.run(search_notes_cmd(args.query, args.limit))
    elif args.command == "stats":
        asyncio.run(show_stats_cmd())
    else:  # Handle no command specified or unknown command
        if args.command is None:
            console = Console()
            console.print(Panel(
                Markdown("# HackMD Notes Explorer\n\nThis CLI tool allows you to explore HackMD notes stored in the database."),
                title="Welcome",
                border_style="green"
            ))
            print("\nAvailable commands:")
        else:
            print(f"Unknown command: {args.command}")
        parser.print_help()

if __name__ == "__main__":
    main()
