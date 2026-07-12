# Gab n' Go

Treat the LLM context window like a filesystem. Concepts (constraints, goals, preferences, observations, references) are files you `push` into context and `pull` back out.

The context is just JSON — [llcat](https://github.com/day50-dev/simple-llm-cli) conversation files. Gab n' Go is the curated store; `push` injects concepts as system messages into those files, `pull` scans them and imports what it finds. No FUSE, no magic — just `cp`-style sync on JSON.

## Concept Schema

Each concept is a JSON object with these fields:

| Field        | Limits                        |
| ------------ | ----------------------------- |
| `type`       | `constraint`, `goal`, `preference`, `observation`, `reference` |
| `description` | Under 50 tokens              |
| `short`      | Under 250 characters          |
| `medium`     | Under 1000 characters         |
| `long`       | Under 2500 characters         |

Example:
```json
{
  "type": "constraint",
  "description": "programming languages",
  "short": "The programming language that we use is C",
  "medium": "We use C17 standard and gcc-13 with a compile target of AMD64. Our build system is cmake"
}
```

## Project Structure

| File               | Purpose                                             |
| ------------------ | --------------------------------------------------- |
| `index.html`       | Web interface — drag-and-drop concept management    |
| `server.py`        | HTTP server serving the UI + API to concepts.json   |
| `concept.py`       | CLI for listing and filtering concepts (Typer)      |
| `concept_mcp.py`   | MCP server exposing concepts as a tool              |
| `cdir.py`          | CLI for listing agents and their context sessions   |
| `config.py`        | Shared llama.cpp model configuration                |
| `concepts.json`    | Sample concept data                                 |
| `schema`           | Concept field constraints                           |
| `instruct.txt`     | Prompt to get an LLM to output concept JSON         |
| `tester.html`      | HTML drag-and-drop prototype for the concept window |
| `pyproject.toml`   | Project metadata and build configuration           |
| `requirements.txt` | Python dependencies                                 |

## Dependencies

```bash
pip install -r requirements.txt
```

- [typer](https://typer.tiangolo.com/) – CLI framework
- [mcp](https://github.com/modelcontextprotocol/python-sdk) – Model Context Protocol SDK
- [rich](https://rich.readthedocs.io/) – terminal formatting
- [chromadb](https://www.trychroma.com/) – vector database for concept storage

## Usage

### CLI — browse, push, pull

```bash
# List all concepts
python concept.py main concepts.json

# Filter by type
python concept.py main concepts.json --type constraint

# Print as an LLM prompt (inject into context window)
python concept.py main concepts.json --type preference --format llm

# Push concepts into an llcat conversation JSON (as system message)
python concept.py push conversation.json

# Push with a specific detail level
python concept.py push conversation.json --scope medium

# Pull concepts from an llcat conversation JSON into the store
python concept.py pull conversation.json
```

### Web Interface — browse, drag-and-drop, import/export

```bash
python server.py
```

Open `http://localhost:8080` in a browser. The web UI lets you:
- Paste concept JSON or load from file
- Browse concepts with type filters
- Drag-and-drop to reorder
- Delete individual concepts
- Export the full concept list back as JSON

### MCP Server — query concepts from any MCP host

```bash
python concept_mcp.py
```

Runs over stdin/stdout. Clients call `get_concept` with optional `type` and `description` to pull concepts into context.

### cdir — ls for LLM context windows

```bash
# List all known agents
python cdir.py --agents

# List sessions for a specific agent
python cdir.py opencode/
python cdir.py claude-code/
python cdir.py codex/

# Sort by time (default) or size
python cdir.py opencode/ -t
python cdir.py opencode/ -s

# Reverse sort order
python cdir.py opencode/ -t -r
python cdir.py opencode/ -s -r

# Export a specific session as JSON (llcat conversation format)
python cdir.py opencode/ses_0ac832e8effeeOjgyeQmTJIaZg
```

cdir (context directory) is like DOS mtools but for LLM context windows. It lists agents and their conversation sessions, showing metadata like creation time, modification time, size, and message count. You can also export individual sessions as JSON in the llcat conversation format.

Supported agents:
- **claude** — Claude Desktop (Anthropic)
- **claude-code** — Claude Code CLI
- **opencode** — opencode CLI
- **codex** — OpenAI Codex CLI

### LLM Integration

Use `instruct.txt` to prompt an LLM to summarize conversation topics as concept JSON. Paste the output into the web interface or save it to `concepts.json`.

## Roadmap

- [x] Concept CRUD CLI + MCP tool
- [x] ChromaDB vector storage
- [x] Basic web interface for browsing and drag-and-drop concept management
- [x] Push/pull sync — `push` concepts into llcat conversation JSON, `pull` them back
- [x] cdir — list agents and export sessions from context windows
- [ ] Web interface push/pull — push/pull from the browser

## Configuration

See `config.py` for model path, context size, GPU layers, and generation params. Default: `models/qwen2.5-3b-instruct-q2_k.gguf`.
