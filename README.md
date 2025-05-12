# HackMD Processor Node for KOI-net v1.0.0

![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Test Coverage](https://img.shields.io/badge/coverage-85%25-yellowgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Support](https://img.shields.io/badge/support-active-brightgreen.svg)

A specialized Knowledge Organization Infrastructure (KOI) node that processes and indexes HackMD notes. This processor node subscribes to HackMD events from sensor nodes, stores the notes in a searchable database, and provides both KOI-net protocol integration and a user-friendly API for accessing the indexed notes.

## Key Benefits

- **Comprehensive Indexing**: Indexes all note content, metadata, and history
- **Advanced Search**: Full-text search across all indexed notes
- **Detailed Tracking**: Complete revision history with timestamps
- **KOI-net Integration**: Seamlessly connects with other nodes in the distributed knowledge network
- **Simple Access**: Clean REST API and CLI tools for retrieving notes

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Examples](#examples)
- [Contributing](#contributing)
- [Testing](#testing)
- [CI/CD & Deployment](#cicd--deployment)
- [Versioning & Changelog](#versioning--changelog)
- [License](#license)
- [Contact & Support](#contact--support)

## Installation

### Using pip

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install koi-net-hackmd-processor
```

### Using Docker

```bash
# Pull the Docker image
docker pull blockscience/hackmd-processor-node:latest

# Run using Docker
docker run -p 8001:8001 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  blockscience/hackmd-processor-node:latest
```

### From Source

```bash
# Clone the repository
git clone https://github.com/BlockScience/koi-net-hackmd-processor.git
cd koi-net-hackmd-processor

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Run tests
pytest
```

## Quick Start

1. Create a configuration file:

```bash
# Create a basic config.yaml
cat > config.yaml << EOF
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
EOF
```

2. Start the processor:

```bash
# Using Python module
python -m hackmd_processor_node

# Alternative using make (if available)
make processor-hackmd
```

## Usage

### Using the CLI

The HackMD Processor comes with a CLI tool for exploring indexed notes:

```bash
# List all indexed notes
python cli.py list

# Show a specific note (formatted with Markdown)
python cli.py show <note-id>

# Show history for a specific note
python cli.py history <note-id>

# Search notes by content
python cli.py search "search term"

# Display statistics about indexed notes
python cli.py stats
```

### Using the API

```python
import requests

# List all notes
response = requests.get("http://localhost:8001/notes")
notes = response.json()
print(f"Found {len(notes)} notes")

# Get a specific note
note_id = "abcdef123456" # Replace with a real note ID
response = requests.get(f"http://localhost:8001/notes/{note_id}")
note = response.json()
print(f"Note title: {note['title']}")
print(f"Content: {note['content'][:100]}...")

# Search notes
response = requests.get("http://localhost:8001/search", params={"query": "important topic"})
search_results = response.json()
print(f"Found {len(search_results)} notes matching the search query")
```

## Configuration

The processor is configured using a YAML file with the following options:

| Option                           | Default                             | Description                         | Required |
| -------------------------------- | ----------------------------------- | ----------------------------------- | -------- |
| `server.host`                    | `127.0.0.1`                         | Host address to bind the server to  | Yes      |
| `server.port`                    | `8001`                              | Port to listen on                   | Yes      |
| `server.path`                    | `/koi-net`                          | Base path for KOI-net API endpoints | Yes      |
| `koi_net.node_name`              | `processor_hackmd`                  | Name of this node                   | Yes      |
| `koi_net.node_rid`               | Generated                           | Unique RID for this node            | No       |
| `koi_net.node_profile.base_url`  | Based on server config              | Base URL for this node's API        | No       |
| `koi_net.node_profile.node_type` | `FULL`                              | Node type (FULL or PARTIAL)         | Yes      |
| `koi_net.node_profile.provides`  | Empty lists                         | RID types provided by this node     | Yes      |
| `koi_net.cache_directory_path`   | `.koi/processor-hackmd/cache`       | Path to cache directory             | Yes      |
| `koi_net.event_queues_path`      | `.koi/processor-hackmd/queues.json` | Path to event queues file           | Yes      |
| `koi_net.first_contact`          | None                                | URL of first node to contact        | No       |
| `index_db_path`                  | `.koi/processor-hackmd/index.db`    | Path to SQLite database             | Yes      |
| `fetch_retry_initial`            | `30`                                | Initial retry delay in seconds      | No       |
| `fetch_retry_multiplier`         | `2`                                 | Backoff multiplier for retries      | No       |
| `fetch_retry_max_attempts`       | `3`                                 | Maximum retry attempts              | No       |

### Sample Configuration File

```yaml
server:
  host: 127.0.0.1
  port: 8001
  path: /koi-net
koi_net:
  node_name: processor_hackmd
  node_rid: orn:koi-net.node:processor_hackmd+62eabec3-ed43-4122-94cc-ea7aa8701fde
  node_profile:
    base_url: http://127.0.0.1:8001/koi-net
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

## API Reference

### KOI-net Protocol Endpoints

All KOI-net protocol endpoints are exposed under the `/koi-net` prefix:

#### POST /koi-net/events/broadcast

Receives events broadcast from other nodes.

**Request Body:**

```json
{
  "events": [
    {
      "rid": "orn:hackmd.note:abcdef123456",
      "event_type": "NEW",
      "manifest": {
        "rid": "orn:hackmd.note:abcdef123456",
        "timestamp": "2023-01-01T12:00:00Z",
        "sha256_hash": "hash123"
      },
      "contents": {}
    }
  ]
}
```

**Response:**

```json
{ "status": "ok" }
```

#### POST /koi-net/events/poll

Allows partial nodes to poll for events.

**Request Body:**

```json
{
  "rid": "orn:koi-net.node:some-node+uuid",
  "limit": 50
}
```

**Response:**

```json
{
  "events": []
}
```

#### POST /koi-net/rids/fetch

Retrieves RIDs of a specific type.

**Request Body:**

```json
{
  "rid_types": ["orn:hackmd.note"]
}
```

**Response:**

```json
{
  "rids": ["orn:hackmd.note:abcdef123456", "orn:hackmd.note:ghijkl789012"]
}
```

#### POST /koi-net/manifests/fetch

Retrieves manifests for specific RIDs.

**Request Body:**

```json
{
  "rids": ["orn:hackmd.note:abcdef123456"]
}
```

**Response:**

```json
{
  "manifests": [
    {
      "rid": "orn:hackmd.note:abcdef123456",
      "timestamp": "2023-01-01T12:00:00Z",
      "sha256_hash": "hash123"
    }
  ],
  "not_found": []
}
```

#### POST /koi-net/bundles/fetch

Retrieves full bundles for specific RIDs.

**Request Body:**

```json
{
  "rids": ["orn:hackmd.note:abcdef123456"]
}
```

**Response:**

```json
{
  "bundles": [
    {
      "manifest": {
        "rid": "orn:hackmd.note:abcdef123456",
        "timestamp": "2023-01-01T12:00:00Z",
        "sha256_hash": "hash123"
      },
      "contents": {
        "title": "Example Note",
        "content": "# Example Note\n\nThis is a note.",
        "lastChangedAt": 1641038400000,
        "createdAt": 1641038400000
      }
    }
  ],
  "not_found": [],
  "deferred": []
}
```

### HackMD Note API Endpoints

#### GET /notes

List all indexed notes.

**Query Parameters:**

- `limit` (optional): Maximum number of notes to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `search` (optional): Filter notes by search term

**Response:**

```json
[
  {
    "id": "abcdef123456",
    "title": "Example Note",
    "updated_at": 1641038400000,
    "event_type": "CACHED",
    "tags": "example,demo",
    "word_count": 42
  }
]
```

#### GET /notes/{note_id}

Get a specific note by ID.

**Response:**

```json
{
  "id": "abcdef123456",
  "title": "Example Note",
  "content": "# Example Note\n\nThis is a note.",
  "updated_at": 1641038400000,
  "created_at": 1641038400000,
  "event_type": "CACHED",
  "tags": "example,demo",
  "word_count": 42
}
```

#### GET /notes/{note_id}/history

Get history for a specific note.

**Query Parameters:**

- `limit` (optional): Maximum number of history entries to return (default: 20)

**Response:**

```json
[
  {
    "id": 1,
    "note_rid": "orn:hackmd.note:abcdef123456",
    "timestamp": "2023-01-01T12:00:00Z",
    "event_type": "NEW",
    "summary": "NEW note: Example Note",
    "bundle_rid": "orn:hackmd.note:abcdef123456"
  }
]
```

#### GET /search

Search notes by content.

**Query Parameters:**

- `query`: Search query
- `limit` (optional): Maximum number of results to return (default: 20)

**Response:**

```json
[
  {
    "id": "abcdef123456",
    "title": "Example Note",
    "updated_at": 1641038400000,
    "event_type": "CACHED",
    "tags": "example,demo",
    "word_count": 42
  }
]
```

#### GET /stats

Get statistics about indexed notes.

**Response:**

```json
{
  "total_notes": 42,
  "total_words": 12345,
  "avg_words_per_note": 294.0,
  "newest_note": {
    "note_id": "abcdef123456",
    "title": "Example Note",
    "last_updated": 1641038400000
  },
  "oldest_note": {
    "note_id": "ghijkl789012",
    "title": "First Note",
    "created_at": 1640995200000
  }
}
```

## Architecture

The HackMD Processor consists of several key components that work together to process HackMD notes:

```
┌─────────────────┐     ┌────────────────┐     ┌────────────────┐
│  HackMD Sensor  │────>│  KOI-net Node  │────>│ Other KOI-net  │
│     (events)    │     │   Interface    │     │     Nodes      │
└─────────────────┘     └────────┬───────┘     └────────────────┘
                                 │
                                 ▼
               ┌─────────────────────────────────┐
               │       Processor Interface       │
               │                                 │
               │  ┌─────────────┐ ┌───────────┐  │
               │  │    Event    │ │  Network  │  │
               │  │  Handlers   │ │  Handlers │  │
               │  └─────────────┘ └───────────┘  │
               └──────────────┬──────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────────────┐
      │            Note Service & Indexer             │
      └─────────────────────┬─────────────────────────┘
                            │
                            ▼
      ┌───────────────────────────────────────────────┐
      │               SQLite Database                 │
      │  ┌────────────┐  ┌─────────────┐  ┌────────┐  │
      │  │   Notes    │  │    Note     │  │  Note  │  │
      │  │  Metadata  │  │  Contents   │  │ History│  │
      │  └────────────┘  └─────────────┘  └────────┘  │
      └───────────────────────────────────────────────┘
                            │
                            ▼
      ┌───────────────────────────────────────────────┐
      │                REST API / CLI                 │
      └───────────────────────────────────────────────┘
```

### Component Responsibilities

- **KOI-net Node Interface**: Handles communication with other nodes in the KOI-net network.
- **Processor Interface**: Processes incoming HackMD note events through a pipeline of handlers.
- **Event Handlers**: Process HackMD note bundles and store them in the database.
- **Network Handlers**: Manage communication with other nodes, including edge negotiation.
- **Note Service & Indexer**: Core service for storing and retrieving notes.
- **SQLite Database**: Stores note metadata, content, and history with full-text search capabilities.
- **REST API**: FastAPI-based API for querying notes.
- **CLI**: Command-line interface for interacting with the notes database.

## Examples

### Processing a New Note

```python
import requests
from rid_types import HackMDNote
from rid_lib.ext import Bundle
from koi_net.protocol.event import EventType

# Example of how a note is processed:

# 1. HackMD Sensor generates a bundle with note content
note_id = "abcdef123456"
note_content = {
    "title": "Important Meeting Notes",
    "content": "# Meeting Notes\n\nDiscussed project timeline and milestones.",
    "lastChangedAt": 1641038400000,
    "createdAt": 1641038400000,
    "tags": ["meeting", "project"]
}

# 2. Create a bundle with this content (normally done by sensor)
note_rid = HackMDNote(note_id)
note_bundle = Bundle.generate(rid=note_rid, contents=note_content)

# 3. Sensor sends event to processor (we're demonstrating the API call here)
event_payload = {
    "events": [
        {
            "rid": str(note_rid),
            "event_type": "NEW",
            "manifest": {
                "rid": str(note_rid),
                "timestamp": "2023-01-01T12:00:00Z",
                "sha256_hash": note_bundle.manifest.sha256_hash
            },
            "contents": note_content
        }
    ]
}

# 4. Send the event to the processor node
response = requests.post(
    "http://localhost:8001/koi-net/events/broadcast",
    json=event_payload
)

# 5. The processor handles the event, indexes the note content
# We can then retrieve the note through the API
response = requests.get(f"http://localhost:8001/notes/{note_id}")
processed_note = response.json()
print(f"Retrieved note: {processed_note['title']}")
```

### Using the CLI to Search Notes

```bash
#!/bin/bash
# This script demonstrates searching for notes with the CLI tool

# Search for notes containing "meeting"
echo "Searching for notes with 'meeting':"
python cli_hackmd.py search "meeting"

# Search for notes containing "project"
echo "Searching for notes with 'project':"
python cli_hackmd.py search "project"

# Show detailed information for a note found in search
NOTE_ID=$(python cli_hackmd.py search "meeting" | grep -o 'abcdef[0-9a-f]*' | head -1)
if [ ! -z "$NOTE_ID" ]; then
    echo "Showing details for note: $NOTE_ID"
    python cli_hackmd.py show $NOTE_ID

    echo "Showing history for note: $NOTE_ID"
    python cli_hackmd.py history $NOTE_ID
fi

# Show overall statistics
echo "Showing statistics for all notes:"
python cli_hackmd.py stats
```

## Contributing

Contributions to the HackMD Processor are welcome! Please follow these steps:

1. **Fork the Repository**

   - Create a fork of the repository on GitHub.

2. **Clone Your Fork**

   ```bash
   git clone https://github.com/YOUR-USERNAME/koi-net-hackmd-processor.git
   cd koi-net-hackmd-processor
   ```

3. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Changes**

   - Implement your changes
   - Add tests for new functionality

5. **Run Tests**

   ```bash
   pytest
   ```

6. **Commit Changes**

   ```bash
   git commit -am "Add your detailed commit message"
   ```

7. **Push to GitHub**

   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**
   - Go to your fork on GitHub and create a pull request to the main repository.

Please adhere to the project's code style and include appropriate tests with your contributions.

## Testing

Run the test suite with:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=hackmd_processor_node

# Generate HTML coverage report
pytest --cov=hackmd_processor_node --cov-report=html
```

## CI/CD & Deployment

The project uses GitHub Actions for continuous integration:

```yaml
name: HackMD Processor CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10"]

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint with flake8
        run: flake8 hackmd_processor_node

      - name: Test with pytest
        run: pytest

      - name: Build package
        run: python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v2
        with:
          name: dist
          path: dist/
```

## Versioning & Changelog

This project follows [Semantic Versioning](https://semver.org/). For a complete list of changes, see the [CHANGELOG.md](CHANGELOG.md) file.

- **Major version**: Incompatible API changes
- **Minor version**: New functionality in a backward-compatible manner
- **Patch version**: Backward-compatible bug fixes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact & Support

### Maintainers

- BlockScience Team - [info@block.science](mailto:info@block.science)

### Get Help

- Issue Tracker: [GitHub Issues](https://github.com/BlockScience/koi-net-hackmd-processor/issues)
- Discussion: [GitHub Discussions](https://github.com/BlockScience/koi-net-hackmd-processor/discussions)

### Community

- KOI-net Community Forum: [community.koi-net.org](https://community.koi-net.org)
