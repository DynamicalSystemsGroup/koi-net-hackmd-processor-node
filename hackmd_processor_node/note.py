import logging
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from rid_types import HackMDNote
from fastapi import HTTPException
from .core import node
from . import index_db

logger = logging.getLogger(__name__)


class HackMDNoteModel(BaseModel):
    """Pydantic model for HackMD Note from bundle contents"""
    title: str
    content: str
    updated_at: str | int = Field(alias="lastChangedAt")
    created_at: str | int = Field(alias="createdAt")
    tags: Optional[List[str]] = None


# Define Pydantic models for response structure
class NoteListItem(BaseModel):
    """Model for list view of notes"""
    id: str
    title: str
    updated_at: str | int
    event_type: str
    tags: Optional[str] = None
    word_count: Optional[int] = None

class NoteDetail(NoteListItem):
    """Model for detailed view of a note"""
    content: str
    created_at: str | int


class HackMDNoteService:
    """Service for HackMD notes operations"""

    def __init__(self, cache):
        self.cache = cache
        # Initialize the database
        logger.info("Initializing database...")
        print(f"Database initialized: {node.config.index_db_path}")
        index_db.initialize_db(node.config.index_db_path)

    def get_all_notes_summary(self, limit: int = 50, offset: int = 0, search_term: Optional[str] = None):
        """Get a list of all notes with basic information"""
        notes_from_db = index_db.get_notes(node.config.index_db_path, limit=limit, offset=offset, search_term=search_term)

        notes_summary = []
        for note in notes_from_db:
            notes_summary.append(NoteListItem(
                id=note.get("note_id", ""),
                title=note.get("title", ""),
                updated_at=note.get("last_updated", ""),
                event_type="CACHED",  # Since it's from the database
                tags=note.get("tags", ""),
                word_count=note.get("word_count", 0)
            ))

        return notes_summary

    def get_note_detail(self, note_id: str):
        """Get detailed information about a specific note"""
        # First try to get from database
        note_from_db = index_db.get_note_by_id(node.config.index_db_path, note_id)

        if note_from_db:
            return NoteDetail(
                id=note_from_db.get("note_id", ""),
                title=note_from_db.get("title", ""),
                content=note_from_db.get("content", ""),
                updated_at=note_from_db.get("last_updated", ""),
                created_at=note_from_db.get("created_at", ""),
                event_type="CACHED",
                tags=note_from_db.get("tags", ""),
                word_count=note_from_db.get("word_count", 0)
            )

        # If not in database, try to get from cache
        try:
            rid = HackMDNote(note_id)
            note_obj = self.cache.read(rid)

            if not note_obj:
                return None

            note_data = note_obj.validate_contents(HackMDNoteModel)

            # Optionally print content as Markdown to console for debugging
            # console = Console()
            # markdown = Markdown(note_data.content)
            # console.print(markdown)

            # Index the note in our database if we found it in cache but not DB
            index_db.add_note(
                db_path=node.config.index_db_path,
                note_rid=str(rid),
                note_id=note_id,
                title=note_data.title,
                content=note_data.content,
                content_hash=note_obj.manifest.sha256_hash,
                created_at=str(note_data.created_at),
                last_updated=str(note_data.updated_at),
                tags=",".join(note_data.tags) if note_data.tags else None
            )

            return NoteDetail(
                id=note_id,
                title=note_data.title,
                content=note_data.content,
                updated_at=note_data.updated_at,
                created_at=note_data.created_at,
                event_type="CACHED",
                tags=",".join(note_data.tags) if note_data.tags else None,
                word_count=len(note_data.content.split())
            )
        except Exception as e:
            logger.error(f"Error retrieving note {note_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing note {note_id}: {str(e)}")

    def search_notes(self, query: str, limit: int = 20):
        """Search for notes by content"""
        search_results = index_db.search_notes_content(node.config.index_db_path, query, limit)

        notes_summary = []
        for note in search_results:
            notes_summary.append(NoteListItem(
                id=note.get("note_id", ""),
                title=note.get("title", ""),
                updated_at=note.get("last_updated", ""),
                event_type="CACHED",
                tags=note.get("tags", ""),
                word_count=note.get("word_count", 0)
            ))

        return notes_summary

    def get_note_history(self, note_id: str, limit: int = 20):
        """Get history for a specific note"""
        # First get the note to get its RID
        note = index_db.get_note_by_id(node.config.index_db_path, note_id)
        if not note:
            return []

        note_rid = note.get("note_rid")
        if not note_rid:
            return []
        return index_db.get_note_history(node.config.index_db_path, note_rid, limit)

    def get_stats(self):
        """Get statistics about the notes"""
        return index_db.get_stats(node.config.index_db_path)

    def process_note_bundle(self, rid: HackMDNote, bundle_data: Dict[str, Any], event_type: str):
        """Process a note bundle from KOI-net and store in database"""
        try:
            note_data = HackMDNoteModel.model_validate(bundle_data)

            # Add to database
            index_db.add_note(
                db_path=node.config.index_db_path,
                note_rid=str(rid),
                note_id=rid.note_id,
                title=note_data.title,
                content=note_data.content,
                content_hash=bundle_data.get("_koi_manifest_hash", ""),  # This field would be added by the bundle handler
                created_at=str(note_data.created_at),
                last_updated=str(note_data.updated_at),
                tags=",".join(note_data.tags) if note_data.tags else None
            )

            # Add to history
            index_db.add_note_history_event(
                db_path=node.config.index_db_path,
                note_rid=str(rid),
                event_type=event_type,
                summary=f"{event_type} note: {note_data.title}",
                bundle_rid=bundle_data.get("_koi_bundle_rid", "")  # This field would be added by the bundle handler
            )

            logger.info(f"Processed note bundle for {rid}: {note_data.title}")
            return True
        except Exception as e:
            logger.error(f"Error processing note bundle for {rid}: {e}")
            return False


# Instantiate the service (assuming node is available)
note_service = HackMDNoteService(node.processor.cache)
