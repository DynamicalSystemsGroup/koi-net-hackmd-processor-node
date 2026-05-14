# koi-net-hackmd-processor-node

A [KOI-net](https://github.com/DynamicalSystemsGroup/koi-net) processor node that subscribes to HackMD note events from a HackMD sensor node, indexes the notes (content, metadata, history) in a local SQLite database, and exposes a REST API for listing, retrieving, searching, and tracking the history of notes across a workspace.

## What this node is and isn't

| Is | Isn't |
|---|---|
| A KOI-net `FullNode` that consumes `HackMDNote` bundles broadcast by a HackMD sensor | A HackMD client — it never calls HackMD APIs directly; sensors do that |
| A queryable index of notes with full content, metadata, and revision history | A real-time editor or collaboration server |
| A SQLite-backed local index with three tables and seven indexes | Distributed storage — each processor instance maintains its own local index |

## Architecture

```
┌───────────────────┐     ┌────────────────┐     ┌──────────────────┐
│  HackMD sensor    │────►│  KOI-net node  │────►│  Other KOI-net   │
│  (HackMDNote      │     │   interface    │     │     nodes        │
│   manifests)      │     │  (server.py)   │     │                  │
└───────────────────┘     └────────┬───────┘     └──────────────────┘
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │   Processor handlers   │
                      │     (handlers.py)      │
                      │   • Network discovery  │
                      │   • Manifest handler   │
                      │   • Bundle handler     │
                      └────────────┬───────────┘
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │      Note service      │
                      │       (note.py)        │
                      │   indexing + retrieval │
                      └────────────┬───────────┘
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │   SQLite index DB      │
                      │    (index_db.py)       │
                      │   • notes              │
                      │   • note_contents      │
                      │   • note_history       │
                      └────────────┬───────────┘
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │  REST API / CLI tool   │
                      │  (server.py, cli.py)   │
                      └────────────────────────┘
```

Network discovery (`handlers.py`): on startup, the node listens for `KoiNetNode` advertisements and proposes a `WEBHOOK` edge to any node whose profile declares it provides `HackMDNote` events. This is how the processor finds and subscribes to sensors automatically.

## Data model (SQLite)

Three tables created on first run (see `index_db.py`):

```sql
CREATE TABLE notes (
    note_rid       TEXT PRIMARY KEY,         -- orn:hackmd.note:<id>
    note_id        TEXT NOT NULL,
    title          TEXT NOT NULL,
    created_at     TIMESTAMP NOT NULL,
    last_updated   TIMESTAMP NOT NULL,
    last_indexed   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE note_contents (
    note_rid     TEXT PRIMARY KEY,
    content      TEXT NOT NULL,
    content_hash TEXT NOT NULL,               -- for change detection
    tags         TEXT,                        -- comma-separated
    word_count   INTEGER,
    FOREIGN KEY (note_rid) REFERENCES notes(note_rid)
);

CREATE TABLE note_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    note_rid    TEXT NOT NULL,
    timestamp   TIMESTAMP NOT NULL,
    event_type  TEXT NOT NULL,                -- NEW / UPDATE / DELETE
    summary     TEXT,
    bundle_rid  TEXT,                         -- pointer to source KOI-net bundle
    FOREIGN KEY (note_rid) REFERENCES notes(note_rid)
);
```

Seven indexes: `idx_notes_id`, `idx_notes_title`, `idx_notes_updated`, `idx_note_history_note`, `idx_note_history_timestamp`, `idx_note_contents_hash`, plus the primary keys above.

## REST API

All endpoints exist as real FastAPI routes in `server.py`. KOI-net protocol endpoints (default base path `/koi-net`):

| Method + path | Purpose |
|---|---|
| `POST /events/broadcast` | Receive event broadcasts from other nodes |
| `POST /events/poll` | Allow partial nodes to poll for events |
| `POST /rids/fetch` | Return RIDs of a given type |
| `POST /manifests/fetch` | Return manifests for given RIDs |
| `POST /bundles/fetch` | Return full bundles for given RIDs |

Application-specific endpoints (under `/`):

| Method + path | Purpose |
|---|---|
| `GET /health` | Liveness probe |
| `GET /notes` | List indexed notes (`limit`, `offset`, `search` query params) |
| `GET /notes/{note_id}` | Full content of a note by HackMD note ID |
| `GET /notes/{note_id}/history` | Revision history; supports `limit` |
| `GET /search` | Full-text search over note content; supports `query`, `limit` |
| `GET /stats` | Aggregate stats (total notes, total words, newest/oldest note) |

## CLI

A standalone CLI in `cli.py` (also available as `cli_hackmd.py` aliased) for inspecting the local index:

| Command | Purpose |
|---|---|
| `python cli.py list` | List all indexed notes (with optional `--limit`, `--search`) |
| `python cli.py show <note-id>` | Render a single note's content as formatted markdown |
| `python cli.py history <note-id>` | Show revision history for a note |
| `python cli.py search "<query>"` | Search notes by content |
| `python cli.py stats` | Display aggregate statistics |

## Install and run

The repo does not have a `pyproject.toml` or `setup.py` — it is not (yet) published to PyPI. Install from source:

```bash
git clone https://github.com/DynamicalSystemsGroup/koi-net-hackmd-processor-node.git
cd koi-net-hackmd-processor-node
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create a `config.yaml` (see Configuration), then run:

```bash
python -m hackmd_processor_node
```

The node starts a Uvicorn server (see `__main__.py`) bound to the host/port from `config.yaml`.

## Configuration

Minimal `config.yaml` (a working example is included in the repo as `config.yaml`):

```yaml
server:
  host: 127.0.0.1
  port: 8001
  path: /koi-net
koi_net:
  node_name: processor_hackmd
  node_profile:
    node_type: FULL
    provides:
      event: []
      state: []
  cache_directory_path: .koi/processor-hackmd/cache
  event_queues_path: .koi/processor-hackmd/queues.json
  first_contact: http://127.0.0.1:8000/koi-net
index_db_path: .koi/processor-hackmd/index.db
fetch_retry_initial: 30
fetch_retry_multiplier: 2
fetch_retry_max_attempts: 3
```

| Key | Default | Description |
|---|---|---|
| `server.host` | `127.0.0.1` | Bind address |
| `server.port` | `8001` | Listen port |
| `server.path` | `/koi-net` | Base path for KOI-net protocol endpoints |
| `koi_net.node_name` | `processor_hackmd` | Logical node identifier |
| `koi_net.node_profile.node_type` | `FULL` | Full vs partial node |
| `koi_net.cache_directory_path` | `.koi/processor-hackmd/cache` | Bundle cache root |
| `koi_net.event_queues_path` | `.koi/processor-hackmd/queues.json` | Persisted event-queue state |
| `koi_net.first_contact` | (none) | URL of a node to register with on startup |
| `index_db_path` | `.koi/processor-hackmd/index.db` | SQLite database path |
| `fetch_retry_initial` | `30` | Initial retry delay (s) when bundle fetches fail |
| `fetch_retry_multiplier` | `2` | Exponential backoff multiplier |
| `fetch_retry_max_attempts` | `3` | Max retry attempts |

## Source layout

```
.
├── hackmd_processor_node/
│   ├── __main__.py           # entrypoint: starts uvicorn
│   ├── core.py               # FullNode instance
│   ├── config.py             # ProcessorNodeConfig schema
│   ├── server.py             # FastAPI app + all REST routes
│   ├── handlers.py           # KOI-net handlers (Network discovery, Manifest, Bundle)
│   ├── note.py               # NoteService (DB writes + content indexing)
│   └── index_db.py           # SQLite schema + connection
├── cli.py                    # Standalone read-only CLI
├── rid_types.py              # HackMDNote RID-type definition
├── config.yaml               # Sample configuration
├── requirements.txt
├── pyrightconfig.json
└── Makefile
```

## Contributing

This node is part of the [koi-net](https://github.com/DynamicalSystemsGroup/koi-net) ecosystem. See the koi-net main repo for contribution guidelines and the broader protocol context.

## License

MIT. See [LICENSE](LICENSE).
