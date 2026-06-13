# Gab n' Go

A lightweight tool for capturing, storing, and retrieving structured **concepts** (constraints, goals, preferences, observations, references) from LLM-powered conversations. Uses ChromaDB for storage and provides both a CLI and an MCP (Model Context Protocol) server.

## Concept Schema

| Field        | Description                       |
| ------------ | --------------------------------- |
| `type`       | `constraint`, `goal`, `preference`, `observation`, or `reference` |
| `description` | Under 50 tokens                  |
| `short`      | Under 250 characters              |
| `medium`     | Under 1000 characters             |
| `long`       | Under 2500 characters             |

## Files

| File               | Purpose                                             |
| ------------------ | --------------------------------------------------- |
| `concept.py`       | CLI for querying concepts (Typer)                   |
| `concept_mcp.py`   | MCP server exposing `get_concept` tool              |
| `config.py`        | Shared llama.cpp model configuration                |
| `concepts.json`    | Sample concept data                                 |
| `schema`           | Concept field constraints                           |
| `instruct.txt`     | Prompt template for LLMs to output concepts         |
| `tester.html`      | HTML drag-and-drop prototype                        |
| `requirements.txt` | Python dependencies                                 |

## Dependencies

```
pip install -r requirements.txt
```

- [typer](https://typer.tiangolo.com/) – CLI framework
- [mcp](https://github.com/modelcontextprotocol/python-sdk) – Model Context Protocol SDK
- [rich](https://rich.readthedocs.io/) – Terminal formatting
- [chromadb](https://www.trychroma.com/) – Vector database

## Usage

### CLI

```bash
# List all concepts as JSON
python concept.py

# Filter by type
python concept.py concepts.json --type constraint

# Filter by description
python concept.py concepts.json --description "programming languages"

# Output as LLM prompt
python concept.py concepts.json --type preference --format llm

# Select scope (short/medium/long)
python concept.py concepts.json --scope medium

# Raw Python repr output
python concept.py concepts.json --format raw
```

### MCP Server

```bash
python concept_mcp.py
```

Runs over stdin/stdout. Any MCP client can call the `get_concept` tool with optional `type` and `description` parameters.

## LLM Integration

Use `instruct.txt` to prompt an LLM to summarize conversation concepts as JSON. The LLM should output an array of objects matching the schema above, then instruct the user to drag-and-drop the text back into Gab n' Go's window.

## Configuration

See `config.py` for llama.cpp model path, context size, GPU layers, and generation parameters. Default model: `models/qwen2.5-3b-instruct-q2_k.gguf`.
