import logging
from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, HTTPException, APIRouter, Query
from koi_net.protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH,
)
from koi_net.protocol.api_models import (
    EventsPayload,
    PollEvents,
    FetchRids,
    RidsPayload,
    FetchManifests,
    ManifestsPayload,
    FetchBundles,
    BundlesPayload,
)
from koi_net.processor.knowledge_object import KnowledgeSource
from .note import NoteDetail, NoteListItem, note_service
from . import index_db
from .core import node

logger = logging.getLogger(__name__)

# Database path - should be in config but using hardcoded path for now

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events for the FastAPI app."""
    logger.info("Starting HackMD Processor node")

    # Initialize the database
    index_db.initialize_db(node.config.index_db_path)

    # Start the KOI-net node
    node.start()

    yield

    logger.info("Shutting down HackMD Processor node")
    node.stop()

app = FastAPI(
    lifespan=lifespan,
    title="KOI-net HackMD Processor API",
    version="1.0.0",
    description="HackMD Processor node for KOI-net"
)

@app.get("/health", tags=["System"])
async def health_check():
    """Basic health check for the service."""
    return {"status": "healthy", "node_id": str(node.identity.rid) if node.identity else "uninitialized"}

# Create a router for KOI-net protocol endpoints
koi_net_router = APIRouter(
    prefix="/koi-net",
    tags=["KOI-net Protocol"]
)

# Create a router for custom note API endpoints
notes_router = APIRouter(
    prefix="",
    tags=["HackMD Notes"]
)

# --- KOI-net standard protocol endpoints ---
@koi_net_router.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload):
    """Process incoming events from other nodes."""
    logger.info(f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)")
    for ev in req.events:
        logger.info(f"{ev!r}")
        node.processor.handle(event=ev, source=KnowledgeSource.External)
    return {"status": "ok"}

@koi_net_router.post(POLL_EVENTS_PATH)
def poll_events(req: PollEvents) -> EventsPayload:
    """Allow other nodes to poll for events."""
    logger.info(f"Request to {POLL_EVENTS_PATH}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)

@koi_net_router.post(FETCH_RIDS_PATH)
def fetch_rids(req: FetchRids) -> RidsPayload:
    """Respond to RID fetch requests."""
    return node.network.response_handler.fetch_rids(req)

@koi_net_router.post(FETCH_MANIFESTS_PATH)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    """Respond to manifest fetch requests."""
    return node.network.response_handler.fetch_manifests(req)

@koi_net_router.post(FETCH_BUNDLES_PATH)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    """Respond to bundle fetch requests."""
    return node.network.response_handler.fetch_bundles(req)

# --- Custom note endpoints ---
@notes_router.get("/notes", response_model=List[NoteListItem])
def list_all_notes(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notes to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    search: Optional[str] = Query(None, description="Optional search term")
):
    """List all notes from local cache, with optional search filtering."""
    try:
        return note_service.get_all_notes_summary(limit=limit, offset=offset, search_term=search)
    except Exception as e:
        logger.error(f"Unexpected error listing notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@notes_router.get("/notes/{note_id}", response_model=NoteDetail)
def get_note_by_id(note_id: str):
    """Get a specific note by ID from local cache."""
    note_detail = note_service.get_note_detail(note_id)
    if note_detail is None:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return note_detail

@notes_router.get("/notes/{note_id}/history")
def get_note_history(
    note_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of history entries to return")
):
    """Get history for a specific note."""
    history = note_service.get_note_history(note_id, limit)
    if not history:
        raise HTTPException(status_code=404, detail=f"No history found for note {note_id}")
    return history

@notes_router.get("/search")
def search_notes(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return")
):
    """Search notes by content."""
    results = note_service.search_notes(query, limit)
    if not results:
        raise HTTPException(status_code=404, detail=f"No notes found matching '{query}'")
    return results

@notes_router.get("/stats")
def get_stats():
    """Get statistics about indexed notes."""
    return note_service.get_stats()

# Include both routers
app.include_router(koi_net_router)
app.include_router(notes_router)

@app.get("/health")
def root():
    """Redirect to API documentation."""
    return {"status": "Healthy"}
