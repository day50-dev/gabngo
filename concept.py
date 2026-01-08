#!/usr/bin/env python3
import typer
import json
import logging
import chromadb
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


if __name__ == "__main__":
    app()
