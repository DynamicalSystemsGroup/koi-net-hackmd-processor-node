import os
import sqlite3
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Define table schemas
SCHEMA_INIT = [
    # Notes tracking table
    """
    CREATE TABLE IF NOT EXISTS notes (
        note_rid TEXT PRIMARY KEY,
        note_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        last_updated TIMESTAMP NOT NULL,
        last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Note content and metadata table
    """
    CREATE TABLE IF NOT EXISTS note_contents (
        note_rid TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        tags TEXT,
        word_count INTEGER,
        FOREIGN KEY (note_rid) REFERENCES notes(note_rid)
    )
    """,

    # Note history table for tracking changes
    """
    CREATE TABLE IF NOT EXISTS note_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_rid TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        event_type TEXT NOT NULL,
        summary TEXT,
        bundle_rid TEXT,
        FOREIGN KEY (note_rid) REFERENCES notes(note_rid)
    )
    """
]

# Create indexes for efficient querying
SCHEMA_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_notes_id ON notes (note_id)",
    "CREATE INDEX IF NOT EXISTS idx_notes_title ON notes (title)",
    "CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes (last_updated)",
    "CREATE INDEX IF NOT EXISTS idx_note_history_note ON note_history (note_rid)",
    "CREATE INDEX IF NOT EXISTS idx_note_history_timestamp ON note_history (timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_note_contents_hash ON note_contents (content_hash)"
]

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Get a SQLite database connection with row factory set to sqlite3.Row.

    Args:
        db_path: Path to the SQLite database

    Returns:
        A connection to the database with row_factory set
    """
    if not os.path.exists(db_path):
        initialize_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(db_path: str) -> None:
    """Initialize the SQLite database with the required schema if it doesn't exist."""
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Connect to the database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    for table_schema in SCHEMA_INIT:
        cursor.execute(table_schema)

    # Create indexes
    for index_schema in SCHEMA_INDEXES:
        cursor.execute(index_schema)

    # Commit and close
    conn.commit()
    conn.close()

    logger.info(f"Initialized database at {db_path}")

def add_note(
    db_path: str,
    note_rid: str,
    note_id: str,
    title: str,
    content: str,
    content_hash: str,
    created_at: str,
    last_updated: str,
    tags: Optional[str] = None
) -> None:
    """Add or update a note in the database."""
    if not os.path.exists(db_path):
        initialize_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if note already exists
        cursor.execute("SELECT 1 FROM notes WHERE note_rid = ?", (note_rid,))
        note_exists = cursor.fetchone() is not None

        if note_exists:
            # Update the note
            cursor.execute(
                """
                UPDATE notes
                SET title = ?, last_updated = ?, last_indexed = CURRENT_TIMESTAMP
                WHERE note_rid = ?
                """,
                (title, last_updated, note_rid)
            )

            # Update note contents
            cursor.execute(
                """
                UPDATE note_contents
                SET content = ?, content_hash = ?, tags = ?, word_count = ?
                WHERE note_rid = ?
                """,
                (content, content_hash, tags, len(content.split()), note_rid)
            )

            event_type = "UPDATE"
        else:
            # Insert new note
            cursor.execute(
                """
                INSERT INTO notes (note_rid, note_id, title, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (note_rid, note_id, title, created_at, last_updated)
            )

            # Insert note contents
            cursor.execute(
                """
                INSERT INTO note_contents (note_rid, content, content_hash, tags, word_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (note_rid, content, content_hash, tags, len(content.split()))
            )

            event_type = "NEW"

        # Record in history
        cursor.execute(
            """
            INSERT INTO note_history (note_rid, timestamp, event_type, summary)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            """,
            (note_rid, event_type, f"{event_type} note: {title}")
        )

        conn.commit()
        logger.info(f"{event_type} note {note_rid} ({title}) recorded in database")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding/updating note {note_rid}: {e}")
        raise
    finally:
        conn.close()

def get_note(db_path: str, note_rid: str) -> Optional[Dict[str, Any]]:
    """Get a complete note by its RID."""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT n.*, nc.content, nc.content_hash, nc.tags, nc.word_count
            FROM notes n
            JOIN note_contents nc ON n.note_rid = nc.note_rid
            WHERE n.note_rid = ?
            """,
            (note_rid,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    except Exception as e:
        logger.error(f"Error retrieving note {note_rid}: {e}")
        return None
    finally:
        conn.close()

def get_note_by_id(db_path: str, note_id: str) -> Optional[Dict[str, Any]]:
    """Get a complete note by its note_id."""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT n.*, nc.content, nc.content_hash, nc.tags, nc.word_count
            FROM notes n
            JOIN note_contents nc ON n.note_rid = nc.note_rid
            WHERE n.note_id = ?
            """,
            (note_id,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    except Exception as e:
        logger.error(f"Error retrieving note by ID {note_id}: {e}")
        return None
    finally:
        conn.close()

def get_notes(
    db_path: str,
    limit: int = 50,
    offset: int = 0,
    search_term: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get a list of notes, optionally filtered by a search term."""
    if not os.path.exists(db_path):
        initialize_db(db_path)
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if search_term:
            # Simple search by title
            cursor.execute(
                """
                SELECT n.note_rid, n.note_id, n.title, n.created_at, n.last_updated,
                       nc.word_count, nc.tags
                FROM notes n
                JOIN note_contents nc ON n.note_rid = nc.note_rid
                WHERE n.title LIKE ? OR nc.content LIKE ?
                ORDER BY n.last_updated DESC
                LIMIT ? OFFSET ?
                """,
                (f'%{search_term}%', f'%{search_term}%', limit, offset)
            )
        else:
            cursor.execute(
                """
                SELECT n.note_rid, n.note_id, n.title, n.created_at, n.last_updated,
                       nc.word_count, nc.tags
                FROM notes n
                JOIN note_contents nc ON n.note_rid = nc.note_rid
                ORDER BY n.last_updated DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )

        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Error retrieving notes: {e}")
        return []
    finally:
        conn.close()

def get_note_history(db_path: str, note_rid: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get the history of a specific note."""
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, note_rid, timestamp, event_type, summary, bundle_rid
            FROM note_history
            WHERE note_rid = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (note_rid, limit)
        )

        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Error retrieving history for note {note_rid}: {e}")
        return []
    finally:
        conn.close()

def add_note_history_event(
    db_path: str,
    note_rid: str,
    event_type: str,
    summary: str,
    bundle_rid: Optional[str] = None
) -> None:
    """Add an event to the note history."""
    if not os.path.exists(db_path):
        initialize_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO note_history (note_rid, timestamp, event_type, summary, bundle_rid)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?)
            """,
            (note_rid, event_type, summary, bundle_rid)
        )

        conn.commit()
        logger.debug(f"Added history event for note {note_rid}: {event_type}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding history event for note {note_rid}: {e}")
    finally:
        conn.close()

def delete_note(db_path: str, note_rid: str) -> bool:
    """Delete a note from the database."""
    if not os.path.exists(db_path):
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # First delete from note_contents (foreign key constraint)
        cursor.execute(
            "DELETE FROM note_contents WHERE note_rid = ?",
            (note_rid,)
        )

        # Add a history entry before deleting the note
        cursor.execute(
            """
            INSERT INTO note_history (note_rid, timestamp, event_type, summary)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            """,
            (note_rid, "DELETE", f"Note {note_rid} deleted")
        )

        # Then delete from notes
        cursor.execute(
            "DELETE FROM notes WHERE note_rid = ?",
            (note_rid,)
        )

        # Note: We intentionally keep the history even after deletion

        rows_affected = cursor.rowcount
        conn.commit()

        logger.info(f"Deleted note {note_rid}")
        return rows_affected > 0

    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting note {note_rid}: {e}")
        return False
    finally:
        conn.close()

def count_notes(db_path: str, search_term: Optional[str] = None) -> int:
    """Count the total number of notes, optionally filtered by a search term."""
    if not os.path.exists(db_path):
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if search_term:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM notes n
                JOIN note_contents nc ON n.note_rid = nc.note_rid
                WHERE n.title LIKE ? OR nc.content LIKE ?
                """,
                (f'%{search_term}%', f'%{search_term}%')
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM notes")

        return cursor.fetchone()[0]

    except Exception as e:
        logger.error(f"Error counting notes: {e}")
        return 0
    finally:
        conn.close()

def search_notes_content(db_path: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search notes by their content with a more advanced query."""
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # More sophisticated search implementation could use FTS5 or other SQLite extensions
        # This is a simple implementation using LIKE
        cursor.execute(
            """
            SELECT n.note_rid, n.note_id, n.title, n.created_at, n.last_updated,
                   nc.word_count, nc.tags,
                   substr(nc.content, 1, 150) || '...' as content_preview
            FROM notes n
            JOIN note_contents nc ON n.note_rid = nc.note_rid
            WHERE nc.content LIKE ? OR n.title LIKE ?
            ORDER BY n.last_updated DESC
            LIMIT ?
            """,
            (f'%{query}%', f'%{query}%', limit)
        )

        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        return []
    finally:
        conn.close()

def get_stats(db_path: str) -> Dict[str, Any]:
    """Get statistics about the notes database."""
    if not os.path.exists(db_path):
        return {
            "total_notes": 0,
            "total_words": 0,
            "avg_words_per_note": 0,
            "newest_note": None,
            "oldest_note": None
        }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Total notes
        cursor.execute("SELECT COUNT(*) as count FROM notes")
        total_notes = cursor.fetchone()["count"]

        # No notes? Return early
        if total_notes == 0:
            return {
                "total_notes": 0,
                "total_words": 0,
                "avg_words_per_note": 0,
                "newest_note": None,
                "oldest_note": None
            }

        # Total words
        cursor.execute("SELECT SUM(word_count) as total FROM note_contents")
        total_words = cursor.fetchone()["total"] or 0

        # Average words per note
        avg_words = total_words / total_notes if total_notes > 0 else 0

        # Newest note
        cursor.execute(
            """
            SELECT note_id, title, last_updated
            FROM notes
            ORDER BY last_updated DESC
            LIMIT 1
            """
        )
        newest_note = dict(cursor.fetchone())

        # Oldest note
        cursor.execute(
            """
            SELECT note_id, title, created_at
            FROM notes
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        oldest_note = dict(cursor.fetchone())

        return {
            "total_notes": total_notes,
            "total_words": total_words,
            "avg_words_per_note": round(avg_words, 1),
            "newest_note": newest_note,
            "oldest_note": oldest_note
        }

    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {
            "total_notes": 0,
            "total_words": 0,
            "avg_words_per_note": 0,
            "newest_note": None,
            "oldest_note": None,
            "error": str(e)
        }
    finally:
        conn.close()

def prune_old_data(db_path: str, days_to_keep: int = 90) -> None:
    """Remove old events and related data beyond a certain age."""
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Only remove history entries, keep the actual notes
        cursor.execute(
            """
            DELETE FROM note_history
            WHERE timestamp < datetime('now', '-' || ? || ' days')
            """,
            (days_to_keep,)
        )

        deleted_events = cursor.rowcount
        conn.commit()
        logger.info(f"Pruned {deleted_events} history entries older than {days_to_keep} days")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error pruning old data: {e}")
    finally:
        conn.close()
