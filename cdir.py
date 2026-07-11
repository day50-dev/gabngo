#!/usr/bin/env python3
"""
cdir - ls for LLM context windows

Lists agents and their conversation sessions, similar to DOS mtools
but for LLM context windows.

Usage:
    cdir                    # List all known agents
    cdir claude/            # List sessions for Claude
    cdir opencode/          # List sessions for opencode
    cdir codex/             # List sessions for codex
"""

import os
import sys
import json
import sqlite3
import typer
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich import box

app = typer.Typer()
console = Console()


@dataclass
class Session:
    """Represents a conversation session from any agent."""
    id: str
    name: str
    ctime: Optional[datetime]
    mtime: Optional[datetime]
    size: int  # in bytes or message count
    path: Optional[str] = None
    model: Optional[str] = None
    message_count: Optional[int] = None


@dataclass
class Agent:
    """Represents an LLM agent with its storage configuration."""
    name: str
    description: str
    base_path: Path
    storage_format: str  # 'json', 'sqlite', 'jsonl'
    session_pattern: Optional[str] = None  # glob pattern for session files


# Agent registry - where each agent stores its conversations
AGENTS = {
    'claude': Agent(
        name='claude',
        description='Claude Desktop (Anthropic)',
        base_path=Path.home() / 'Library/Application Support/Claude-3p',
        storage_format='json',
        session_pattern='local-agent-mode-sessions/**/*.json'
    ),
    'claude-code': Agent(
        name='claude-code',
        description='Claude Code CLI',
        base_path=Path.home() / '.claude',
        storage_format='jsonl',
        session_pattern='projects/**/*.jsonl'
    ),
    'opencode': Agent(
        name='opencode',
        description='opencode CLI',
        base_path=Path.home() / '.local/share/opencode',
        storage_format='sqlite'
    ),
    'codex': Agent(
        name='codex',
        description='OpenAI Codex CLI',
        base_path=Path.home() / '.codex',
        storage_format='jsonl',
        session_pattern='sessions/**/*.jsonl'
    ),
}


def get_file_metadata(path: Path) -> tuple:
    """Get creation time, modification time, and size of a file."""
    stat = path.stat()
    ctime = datetime.fromtimestamp(stat.st_ctime)
    mtime = datetime.fromtimestamp(stat.st_mtime)
    size = stat.st_size
    return ctime, mtime, size


def get_claude_sessions(agent: Agent) -> List[Session]:
    """Extract sessions from Claude Desktop."""
    sessions = []
    if not agent.base_path.exists():
        return sessions
    
    for session_file in agent.base_path.glob(agent.session_pattern):
        try:
            ctime, mtime, size = get_file_metadata(session_file)
            
            # Try to extract session info from JSON
            with open(session_file, 'r') as f:
                data = json.load(f)
            
            session_id = session_file.stem
            name = data.get('name', session_id[:8])
            
            sessions.append(Session(
                id=session_id,
                name=name,
                ctime=ctime,
                mtime=mtime,
                size=size,
                path=str(session_file)
            ))
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    
    return sessions


def get_claude_code_sessions(agent: Agent) -> List[Session]:
    """Extract sessions from Claude Code CLI."""
    sessions = []
    if not agent.base_path.exists():
        return sessions
    
    for session_file in agent.base_path.glob(agent.session_pattern):
        try:
            ctime, mtime, size = get_file_metadata(session_file)
            
            # Claude Code uses JSONL format
            with open(session_file, 'r') as f:
                lines = f.readlines()
            
            session_id = session_file.stem
            name = session_id[:8]
            
            # Try to extract name from first message
            if lines:
                try:
                    first_msg = json.loads(lines[0])
                    if 'type' in first_msg and first_msg['type'] == 'human':
                        name = first_msg.get('message', {}).get('content', name)[:50]
                except (json.JSONDecodeError, KeyError):
                    pass
            
            sessions.append(Session(
                id=session_id,
                name=name,
                ctime=ctime,
                mtime=mtime,
                size=size,
                path=str(session_file),
                message_count=len(lines)
            ))
        except (OSError, IndexError):
            continue
    
    return sessions


def get_opencode_sessions(agent: Agent) -> List[Session]:
    """Extract sessions from opencode SQLite database."""
    sessions = []
    db_path = agent.base_path / 'opencode.db'
    
    if not db_path.exists():
        return sessions
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Query sessions table with actual column names
        # Columns: id, title, time_created (ms), time_updated (ms), 
        #          tokens_input, tokens_output, model, directory
        cursor.execute('''
            SELECT id, title, time_created, time_updated, 
                   tokens_input, tokens_output, model, directory
            FROM session 
            ORDER BY time_updated DESC
        ''')
        
        for row in cursor.fetchall():
            session_id, title, time_created, time_updated, tokens_input, tokens_output, model, directory = row
            
            # Parse timestamps (milliseconds since epoch)
            ctime = None
            mtime = None
            if time_created:
                try:
                    ctime = datetime.fromtimestamp(time_created / 1000)
                except (ValueError, TypeError, OSError):
                    pass
            if time_updated:
                try:
                    mtime = datetime.fromtimestamp(time_updated / 1000)
                except (ValueError, TypeError, OSError):
                    pass
            
            # Calculate size from tokens
            size = (tokens_input or 0) + (tokens_output or 0)
            
            # Get message count from message table
            msg_count = None
            try:
                cursor.execute('SELECT COUNT(*) FROM message WHERE session_id = ?', (session_id,))
                msg_count = cursor.fetchone()[0]
            except sqlite3.Error:
                pass
            
            sessions.append(Session(
                id=session_id,
                name=title or session_id[:8],
                ctime=ctime,
                mtime=mtime,
                size=size,
                path=str(db_path),
                model=model,
                message_count=msg_count
            ))
        
        conn.close()
    except sqlite3.Error:
        pass
    
    return sessions


def get_codex_sessions(agent: Agent) -> List[Session]:
    """Extract sessions from OpenAI Codex CLI."""
    sessions = []
    if not agent.base_path.exists():
        return sessions
    
    # Check for SQLite index first (more reliable)
    sqlite_path = agent.base_path / 'state_5.sqlite'
    if sqlite_path.exists():
        try:
            conn = sqlite3.connect(str(sqlite_path))
            cursor = conn.cursor()
            
            # Query sessions from SQLite
            cursor.execute('''
                SELECT id, title, cwd, model, created_at, updated_at
                FROM sessions 
                ORDER BY updated_at DESC
            ''')
            
            for row in cursor.fetchall():
                session_id, title, cwd, model, created_at, updated_at = row
                
                ctime = None
                mtime = None
                if created_at:
                    try:
                        ctime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
                if updated_at:
                    try:
                        mtime = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
                
                sessions.append(Session(
                    id=session_id,
                    name=title or session_id[:8],
                    ctime=ctime,
                    mtime=mtime,
                    size=0,  # Will be updated from rollout files
                    path=str(sqlite_path),
                    model=model
                ))
            
            conn.close()
        except sqlite3.Error:
            pass
    
    # Fall back to JSONL rollout files
    if not sessions:
        for session_file in agent.base_path.glob(agent.session_pattern):
            try:
                ctime, mtime, size = get_file_metadata(session_file)
                
                session_id = session_file.stem
                name = session_id[:8]
                
                # Try to extract metadata from first line
                with open(session_file, 'r') as f:
                    first_line = f.readline()
                    if first_line:
                        try:
                            data = json.loads(first_line)
                            if 'session_meta' in data:
                                meta = data['session_meta']
                                session_id = meta.get('id', session_id)
                                name = meta.get('title', name)
                        except json.JSONDecodeError:
                            pass
                
                sessions.append(Session(
                    id=session_id,
                    name=name,
                    ctime=ctime,
                    mtime=mtime,
                    size=size,
                    path=str(session_file)
                ))
            except OSError:
                continue
    
    return sessions


# Session extractors for each agent
SESSION_EXTRACTORS = {
    'claude': get_claude_sessions,
    'claude-code': get_claude_code_sessions,
    'opencode': get_opencode_sessions,
    'codex': get_codex_sessions,
}


def format_size(size: int) -> str:
    """Format size in human-readable format."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M")


@app.command()
def main(
    agent: Optional[str] = typer.Argument(None, help="Agent name (e.g., claude, opencode, codex)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON")
):
    """
    List agents and their conversation sessions.
    
    Without arguments, lists all known agents.
    With an agent name, lists sessions for that agent.
    """
    if agent is None:
        # List all agents
        table = Table(title="Available Agents", box=box.ROUNDED)
        table.add_column("Agent", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Storage", style="dim")
        table.add_column("Format", style="green")
        
        for name, agent_info in AGENTS.items():
            exists = "✓" if agent_info.base_path.exists() else "✗"
            table.add_row(
                f"{name} {exists}",
                agent_info.description,
                str(agent_info.base_path),
                agent_info.storage_format
            )
        
        console.print(table)
        console.print("\n[dim]Use 'cdir <agent>/' to list sessions[/dim]")
    else:
        # Strip trailing slash if present
        agent_name = agent.rstrip('/')
        
        if agent_name not in AGENTS:
            console.print(f"[red]Unknown agent: {agent_name}[/red]")
            console.print(f"[dim]Available agents: {', '.join(AGENTS.keys())}[/dim]")
            raise typer.Exit(1)
        
        agent_info = AGENTS[agent_name]
        
        if not agent_info.base_path.exists():
            console.print(f"[yellow]Agent path not found: {agent_info.base_path}[/yellow]")
            console.print(f"[dim]Is {agent_name} installed?[/dim]")
            raise typer.Exit(1)
        
        # Get sessions for this agent
        extractor = SESSION_EXTRACTORS.get(agent_name)
        if not extractor:
            console.print(f"[red]No session extractor for {agent_name}[/red]")
            raise typer.Exit(1)
        
        sessions = extractor(agent_info)
        
        if json_output:
            # JSON output
            output = []
            for s in sessions:
                output.append({
                    'id': s.id,
                    'name': s.name,
                    'ctime': s.ctime.isoformat() if s.ctime else None,
                    'mtime': s.mtime.isoformat() if s.mtime else None,
                    'size': s.size,
                    'path': s.path,
                    'model': s.model,
                    'message_count': s.message_count
                })
            print(json.dumps(output, indent=2))
        else:
            # Table output
            if not sessions:
                console.print(f"[yellow]No sessions found for {agent_name}[/yellow]")
                return
            
            table = Table(title=f"{agent_info.description} Sessions", box=box.ROUNDED)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("Created", style="dim")
            table.add_column("Modified", style="dim")
            table.add_column("Size", style="green", justify="right")
            table.add_column("Messages", style="magenta", justify="right")
            
            for s in sessions:
                table.add_row(
                    s.id[:12] + "..." if len(s.id) > 12 else s.id,
                    s.name[:40] + "..." if len(s.name) > 40 else s.name,
                    format_datetime(s.ctime),
                    format_datetime(s.mtime),
                    format_size(s.size),
                    str(s.message_count) if s.message_count else "N/A"
                )
            
            console.print(table)
            console.print(f"\n[dim]{len(sessions)} session(s) found[/dim]")


if __name__ == "__main__":
    app()
