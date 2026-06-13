import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from concept import app, Concept

runner = CliRunner()

SAMPLE_CONCEPTS = [
    {
        "type": "constraint",
        "description": "programming languages",
        "short": "The programming language that we use is C",
        "medium": "We use C17 standard and gcc-13 with a compile target of AMD64. Our build system is cmake",
    },
    {
        "type": "preference",
        "description": "programming style",
        "short": "prefer single character variable names preceded with underscores",
        "medium": "Write C using the K&R (1TBS) style",
    },
]

SAMPLE_CONVERSATION = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."},
]


# --- Concept class tests ---

def test_get_concept_all(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    con.load(str(p))
    res = con.get_concept()
    assert len(res) == 2


def test_get_concept_by_type(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    con.load(str(p))
    res = con.get_concept(klass="constraint")
    assert len(res) == 1
    assert res[0]["type"] == "constraint"


def test_get_concept_by_type_no_match(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    con.load(str(p))
    res = con.get_concept(klass="goal")
    assert len(res) == 2


def test_get_concept_by_description(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    con.load(str(p))
    res = con.get_concept(description="programming languages")
    assert len(res) == 1
    assert res[0]["description"] == "programming languages"


def test_get_concept_by_description_no_match(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    con.load(str(p))
    res = con.get_concept(description="nonexistent")
    assert len(res) == 2


def test_get_concept_empty(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text("[]")
    con = Concept(path=str(p))
    con.load(str(p))
    res = con.get_concept()
    assert res == []


def test_get_concept_triggers_load(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    res = con.get_concept()
    assert len(res) == 2


def test_load_concept_builds_messages(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    con.load(str(p))
    con.load_concept()
    assert len(con) == 1
    assert con[0]["role"] == "system"
    assert "Use the following constraint" in con[0]["content"]
    assert "Use the following preference" in con[0]["content"]


def test_load_concept_with_type_filter(tmp_path):
    p = tmp_path / "concepts.json"
    p.write_text(json.dumps(SAMPLE_CONCEPTS))
    con = Concept(path=str(p))
    con.load(str(p))
    con.load_concept(klass="constraint")
    assert "Use the following constraint" in con[0]["content"]
    assert "Use the following preference" not in con[0]["content"]


# --- Push tests ---

def test_push_adds_system_message(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps(SAMPLE_CONVERSATION))

    con = Concept(path=str(cfile))
    con.load(str(cfile))
    con.push(str(conv))

    data = json.loads(conv.read_text())
    assert len(data) == 4
    assert data[0]["role"] == "system"
    assert "Use the following constraint" in data[0]["content"]
    assert "Use the following preference" in data[0]["content"]


def test_push_replaces_existing_gabngo_message(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    conv = tmp_path / "conv.json"
    convo = list(SAMPLE_CONVERSATION)
    convo.insert(0, {"role": "system", "content": "Use the following constraint: old constraint"})
    conv.write_text(json.dumps(convo))

    con = Concept(path=str(cfile))
    con.load(str(cfile))
    con.push(str(conv))

    data = json.loads(conv.read_text())
    assert len(data) == 4
    assert "old constraint" not in data[0]["content"]
    assert "The programming language that we use is C" in data[0]["content"]


def test_push_empty_concepts(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text("[]")
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps(SAMPLE_CONVERSATION))

    con = Concept(path=str(cfile))
    con.load(str(cfile))
    con.push(str(conv))

    data = json.loads(conv.read_text())
    assert len(data) == 3


def test_push_with_scope(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps(SAMPLE_CONVERSATION))

    con = Concept(path=str(cfile))
    con.load(str(cfile))
    con.push(str(conv), scope="medium")

    data = json.loads(conv.read_text())
    assert "We use C17 standard" in data[0]["content"]
    assert "K&R (1TBS) style" in data[0]["content"]


# --- Pull tests ---

def test_pull_extracts_concepts(tmp_path):
    dest = tmp_path / "concepts.json"
    dest.write_text("[]")
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps([
        {"role": "system", "content": (
            "Use the following constraint: The programming language that we use is C\n"
            "Use the following preference: prefer single character variable names"
        )},
    ]))

    con = Concept(path=str(dest))
    con.pull(str(conv))

    data = json.loads(dest.read_text())
    assert len(data) == 2
    assert data[0]["type"] == "constraint"
    assert data[1]["type"] == "preference"


def test_pull_appends_to_existing(tmp_path):
    dest = tmp_path / "concepts.json"
    dest.write_text(json.dumps(SAMPLE_CONCEPTS))
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps([
        {"role": "system", "content": "Use the following goal: new goal"},
    ]))

    con = Concept(path=str(dest))
    con.pull(str(conv))

    data = json.loads(dest.read_text())
    assert len(data) == 3


def test_pull_no_concepts_found(tmp_path):
    dest = tmp_path / "concepts.json"
    dest.write_text("[]")
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps(SAMPLE_CONVERSATION))

    con = Concept(path=str(dest))
    con.pull(str(conv))

    data = json.loads(dest.read_text())
    assert data == []


def test_pull_ignores_non_concept_lines(tmp_path):
    dest = tmp_path / "concepts.json"
    dest.write_text("[]")
    conv = tmp_path / "conv.json"
    convo = list(SAMPLE_CONVERSATION)
    convo.append({"role": "user", "content": "Use the following something: blah"})
    conv.write_text(json.dumps(convo))

    con = Concept(path=str(dest))
    con.pull(str(conv))

    data = json.loads(dest.read_text())
    assert data == []


# --- CLI tests ---

def test_cli_list_all(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    result = runner.invoke(app, ["main", str(cfile)])
    assert result.exit_code == 0
    assert "constraint" in result.stdout
    assert "preference" in result.stdout


def test_cli_filter_by_type(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    result = runner.invoke(app, ["main", str(cfile), "--type", "constraint"])
    assert result.exit_code == 0
    assert "constraint" in result.stdout
    assert "preference" not in result.stdout


def test_cli_format_llm(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    result = runner.invoke(app, ["main", str(cfile), "--format", "llm"])
    assert result.exit_code == 0
    assert "Use the following constraint" in result.stdout
    assert "Use the following preference" in result.stdout


def test_cli_format_raw(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    result = runner.invoke(app, ["main", str(cfile), "--format", "raw"])
    assert result.exit_code == 0
    assert "constraint" in result.stdout


def test_cli_format_json(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    result = runner.invoke(app, ["main", str(cfile), "--format", "json"])
    assert result.exit_code == 0
    assert "constraint" in result.stdout


def test_cli_push(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps(SAMPLE_CONVERSATION))
    result = runner.invoke(app, ["push", str(conv), "--source", str(cfile)])
    assert result.exit_code == 0
    data = json.loads(conv.read_text())
    assert len(data) == 4
    assert "Use the following constraint" in data[0]["content"]


def test_cli_push_with_scope(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps(SAMPLE_CONVERSATION))
    result = runner.invoke(app, ["push", str(conv), "--scope", "medium", "--source", str(cfile)])
    assert result.exit_code == 0
    data = json.loads(conv.read_text())
    assert "We use C17 standard" in data[0]["content"]


def test_cli_pull(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text("[]")
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps([
        {"role": "system", "content": (
            "Use the following constraint: The programming language that we use is C\n"
            "Use the following preference: prefer single character variable names"
        )},
    ]))
    result = runner.invoke(app, ["pull", str(conv), "--source", str(cfile)])
    assert result.exit_code == 0
    data = json.loads(cfile.read_text())
    assert len(data) == 2


def test_cli_pull_no_concepts(tmp_path):
    cfile = tmp_path / "concepts.json"
    cfile.write_text(json.dumps(SAMPLE_CONCEPTS))
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps(SAMPLE_CONVERSATION))
    result = runner.invoke(app, ["pull", str(conv), "--source", str(cfile)])
    assert result.exit_code == 0
    data = json.loads(cfile.read_text())
    assert len(data) == 2
