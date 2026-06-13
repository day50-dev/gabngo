#!/usr/bin/env python3
import typer
import json
import logging
import chromadb
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax

app = typer.Typer()
client = chromadb.Client()

class Concept(list):
    def __init__(self, path = 'concepts.json', klass = None, description = None):
        super().__init__()
        self.is_loaded = False
        self.db_all = None
        self.collection = client.create_collection("concepts")

    def __str__(self):
        return "\n".join(super().__iter__())

    def load(self, path = 'concepts.json'):
        with open(path, 'r') as f:
            self.db_all = json.load(f)
            self.collection.add(
                documents=[json.dumps(m) for m in self.db_all],
                ids=[str(x) for x in range(0, len(self.db_all))]
            )

    def load_concept(self, klass = None, description = None):
        initial = {'role': 'system', 'content': ""}

        if self.is_loaded:
            initial = super().pop(0)
        
        self.is_loaded = True
        prompt = []
        for x in self.get_concept(klass = klass, description=description):
            prompt.append(f"Use the following {x.get('type')}: {x.get('short')}")
        
        initial['content'] += "\n".join(prompt) + "\n"
        super().insert(0, initial)


    def get_concept(self, klass = None, description = None):
        if self.db_all is None:
            self.load() 

        res = self.db_all
        if klass is not None:
            res_new = list(filter(lambda x: x.get('type') == klass, res))
            if len(res_new) == 0:
                res_new = res
            res = res_new
                

        if description is not None:
            #res = self.collection.query(query_texts=[description], n_results=10)
            #print(res)
            res_new = list(filter(lambda x: x.get('description') == description, res))
            if len(res_new) == 0:
                res_new = res
            res = res_new

        return list(res)

    def push(self, conversation_path, scope="short"):
        """Push concepts as a system message into an llcat conversation JSON."""
        convo = self._load_conversation(conversation_path)
        lines = []
        for x in self.get_concept():
            lines.append(f"Use the following {x.get('type')}: {x.get(scope)}")

        content = "\n".join(lines)
        if not content:
            return

        # Find existing gabn'go system message and replace, or insert one
        replaced = False
        for msg in convo:
            if msg.get("role") == "system" and msg.get("content", "").startswith("Use the following"):
                msg["content"] = content
                replaced = True
                break

        if not replaced:
            convo.insert(0, {"role": "system", "content": content})

        self._save_conversation(conversation_path, convo)

    def pull(self, conversation_path):
        """Pull concepts from an llcat conversation JSON into the concept store."""
        convo = self._load_conversation(conversation_path)
        found = []
        for msg in convo:
            c = msg.get("content", "")
            # Look for "Use the following <type>: <text>" patterns
            for line in c.split("\n"):
                line = line.strip()
                if line.startswith("Use the following "):
                    rest = line[len("Use the following "):]
                    if ": " in rest:
                        k, v = rest.split(": ", 1)
                        k = k.strip()
                        v = v.strip()
                        if k in ("constraint", "goal", "preference", "observation", "reference"):
                            found.append({
                                "type": k,
                                "description": v[:50],
                                "short": v[:250],
                                "medium": v[:1000],
                                "long": v[:2500]
                            })

        if not found:
            return

        existing = self._load_concepts()
        existing.extend(found)
        self._save_concepts(existing)
        self.db_all = existing

    def _load_conversation(self, path):
        with open(path, "r") as f:
            return json.load(f)

    def _save_conversation(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def _load_concepts(self):
        path = Path("concepts.json")
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _save_concepts(self, data):
        with open("concepts.json", "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")


@app.command()
def main(
  path: typer.FileText = typer.Argument("concepts.json", help="The concept file to read."),
  type: str = typer.Option("", help="the type of the concept"),
  description: str = typer.Option("", help="a description of the concept"),
  format: str=typer.Option("json", help="output style: raw, json or llm"),
  scope: str=typer.Option("short", help="short, medium or large")
  ):

    con = Concept(path = path)
    console = Console()
    res = con.get_concept(klass = type, description = description)
    if format == "json":
        console.print_json(data=res)
    elif format == "raw":
        print(res)
    elif format == "llm":
        prompt = []
        for x in res:
            prompt.append(f"Use the following {x.get('type')}: {x.get(scope)}")

        print("\n".join(prompt))


@app.command()
def push(
    conversation: Path = typer.Argument(..., help="llcat conversation JSON to inject into"),
    scope: str = typer.Option("short", help="short, medium or long"),
    source: str = typer.Option("concepts.json", help="concept store file")
):
    """Push concepts into an llcat conversation JSON as system messages."""
    con = Concept(path=source)
    con.load(source)
    con.push(conversation, scope=scope)
    print(f"Pushed concepts into {conversation}")


@app.command()
def pull(
    conversation: Path = typer.Argument(..., help="llcat conversation JSON to scan"),
    source: str = typer.Option("concepts.json", help="concept store file")
):
    """Pull concepts from an llcat conversation JSON into the concept store."""
    con = Concept(path=source)
    con.pull(conversation)
    print(f"Pulled concepts from {conversation} into {source}")


if __name__ == "__main__":
    app()
