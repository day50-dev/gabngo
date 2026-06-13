# Gab n' Go

Treat the LLM context window as a filesystem. Concepts (constraints, goals, preferences, observations, references) are files that can be moved in and out of context, stored, queried, and retrieved.

Long-term goal: mount the context window as a FUSE filesystem and interact with it directly — putting in and removing memories as concept chunks.

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
| `concept.py`       | CLI for listing and filtering concepts (Typer)      |
| `concept_mcp.py`   | MCP server exposing concepts as a tool              |
| `config.py`        | Shared llama.cpp model configuration                |
| `concepts.json`    | Sample concept data                                 |
| `schema`           | Concept field constraints                           |
| `instruct.txt`     | Prompt to get an LLM to output concept JSON         |
| `tester.html`      | HTML drag-and-drop prototype for the concept window |
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

### CLI — browse concepts like `ls`

```bash
# List all concepts
python concept.py

# Filter by type
python concept.py concepts.json --type constraint

# Filter by description
python concept.py concepts.json --description "programming languages"

# Print as an LLM prompt (inject into context window)
python concept.py concepts.json --type preference --format llm

# Select detail level
python concept.py concepts.json --scope medium
```

### MCP Server — query concepts from any MCP host

```bash
python concept_mcp.py
```

Runs over stdin/stdout. Clients call `get_concept` with optional `type` and `description` to pull concepts into context.

### LLM Integration

Use `instruct.txt` to prompt an LLM to summarize conversation topics as concept JSON. The output gets loaded into the web interface where concepts can be browsed and managed.

## Roadmap

- [x] Concept CRUD CLI + MCP tool
- [x] ChromaDB vector storage
- [ ] Basic web interface for browsing and drag-and-drop concept management
- [ ] FUSE filesystem mount for the context window
- [ ] Bidirectional sync — context ↔ filesystem

## Configuration

See `config.py` for model path, context size, GPU layers, and generation params. Default: `models/qwen2.5-3b-instruct-q2_k.gguf`.
