#!/usr/bin/env python3
"""
Example Project Auto-Compact Script

When context becomes too large, automatically:
1. Full backup of current conversation (jsonl parsing)
2. Generate intelligent summary using Claude Code
3. Save to ChromaDB
4. Save recovery information
"""

import gzip
import json
import os
import select
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich import box

from common.config import load_auto_compact_config
from common.logger import HookLogger
from common.sentry import init_sentry, capture_exception, add_breadcrumb, flush

console = Console(stderr=True)


def find_project_root() -> Optional[Path]:
    """
    Example Project
    Automatically detects the project root
    Finds the root directory containing `pyproject.toml` with `project_sample`
    """
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        project_path = Path(project_dir)
        if project_path.exists() and (project_path / ".claude").exists():
            return project_path

    current = Path.cwd()
    for parent in [current] + list(current.parents):
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding='utf-8')
                if 'project_sample' in content.lower() or 'example_project' in content:
                    if (parent / ".claude").exists():
                        return parent
            except Exception:
                pass

        if (parent / ".git").exists() and (parent / ".claude").exists():
            return parent

    return None


def parse_transcript_jsonl(transcript_path: Path) -> Dict[str, Any]:
    """Parse JSONL files and return structured data"""
    messages = []
    file_history = {'snapshots': [], 'tracked_files': {}}

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get('type')

                if entry_type == 'user':
                    msg = entry.get('message', {})
                    messages.append({
                        'uuid': entry.get('uuid'),
                        'type': 'user',
                        'timestamp': entry.get('timestamp'),
                        'content': msg.get('content', ''),
                        'metadata': {
                            'cwd': entry.get('cwd'),
                            'git_branch': entry.get('git_branch'),
                            'is_sidechain': entry.get('isSidechain', False)
                        }
                    })

                elif entry_type == 'assistant':
                    msg = entry.get('message', {})
                    messages.append({
                        'uuid': entry.get('uuid'),
                        'type': 'assistant',
                        'timestamp': entry.get('timestamp'),
                        'content': msg.get('content', []),
                        'model': msg.get('model'),
                        'usage': msg.get('usage', {}),
                        'stop_reason': msg.get('stop_reason')
                    })

                elif entry_type == 'file-history-snapshot':
                    snapshot = entry.get('snapshot', {})
                    file_history['snapshots'].append({
                        'message_id': snapshot.get('messageId'),
                        'timestamp': snapshot.get('timestamp'),
                        'tracked_files': snapshot.get('trackedFileBackups', {})
                    })

    except FileNotFoundError:
        console.print(f"[yellow]WARNING: Transcript file not found: {transcript_path}[/]")
    except Exception as e:
        console.print(f"[yellow]WARNING: Error during transcript parsing: {e}[/]")

    return {
        'messages': messages,
        'file_history': file_history
    }


def calculate_statistics(conversation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Conversation Statistics Calculation"""
    messages = conversation_data.get('messages', [])

    user_messages = [m for m in messages if m.get('type') == 'user']
    assistant_messages = [m for m in messages if m.get('type') == 'assistant']

    total_tokens = 0
    for msg in assistant_messages:
        usage = msg.get('usage', {})
        total_tokens += usage.get('input_tokens', 0)
        total_tokens += usage.get('output_tokens', 0)
        total_tokens += usage.get('cache_read_input_tokens', 0)

    if messages:
        first_ts = messages[0].get('timestamp', '')
        last_ts = messages[-1].get('timestamp', '')
        try:
            first_dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
            last_dt = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            duration_seconds = (last_dt - first_dt).total_seconds()
        except (ValueError, AttributeError):
            duration_seconds = 0
    else:
        duration_seconds = 0

    return {
        'total_messages': len(messages),
        'user_messages': len(user_messages),
        'assistant_messages': len(assistant_messages),
        'total_tokens': total_tokens,
        'conversation_duration_seconds': int(duration_seconds),
        'file_snapshots': len(conversation_data.get('file_history', {}).get('snapshots', []))
    }


def backup_conversation(
    conversation: str,
    config: Dict[str, Any]
) -> tuple[Optional[Path], Optional[Dict[str, Any]]]:
    """
    Complete backup of conversation content (including JSONL parsing)

    Returns:
        (backup_file, backup_data) Tuple
    """
    backup_config = config['backup']

    if not backup_config['enabled']:
        return None, None

    project_root = find_project_root()
    if project_root:
        backup_location = project_root / ".claude" / "backups"
    else:
        backup_location = Path(backup_config['backup_location'])

    backup_location.mkdir(parents=True, exist_ok=True)

    try:
        session_meta = json.loads(conversation)
    except json.JSONDecodeError:
        console.print("[yellow]WARNING: Session metadata parsing failed; backing up as text.[/]")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_location / f"conversation_{timestamp}.txt"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(conversation)
        return backup_file, None

    transcript_path = Path(session_meta.get('transcript_path', ''))

    if not transcript_path.exists():
        console.print(f"[yellow]WARNING: The transcript file does not exist.: {transcript_path}[/]")
        conversation_data = {'messages': [], 'file_history': {}}
    else:
        conversation_data = parse_transcript_jsonl(transcript_path)

    backup_data = {
        'backup_metadata': {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'session_id': session_meta.get('session_id'),
            'cwd': session_meta.get('cwd'),
            'git_branch': session_meta.get('git_branch'),
            'original_transcript_path': str(transcript_path),
            'hook_event': session_meta.get('hook_event_name'),
            'trigger': session_meta.get('trigger')
        },
        'conversation': conversation_data['messages'],
        'file_history': conversation_data['file_history'],
        'statistics': calculate_statistics(conversation_data)
    }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    use_compression = backup_config['compress']

    if use_compression:
        backup_file = backup_location / f"conversation_{timestamp}.json.gz"
        with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)  # type: ignore[arg-type]
    else:
        backup_file = backup_location / f"conversation_{timestamp}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

    console.print(f"[green]OK[/] Create backup: {backup_file}")
    console.print(f"   Message: {backup_data['statistics']['total_messages']}")
    console.print(f"   Token: {backup_data['statistics']['total_tokens']:,}")
    console.print(f"   Period: {backup_data['statistics']['conversation_duration_seconds']}")

    max_backups = backup_config['max_backups']
    cleanup_old_backups(backup_location, max_backups)

    return backup_file, backup_data


def cleanup_old_backups(backup_dir: Path, max_backups: int) -> None:
    """Cleaning Up Old Backup Files"""
    backups = sorted(backup_dir.glob('conversation_*.*'))

    if len(backups) > max_backups:
        for backup in backups[:-max_backups]:
            backup.unlink()
            console.print(f"Delete: {backup.name}")


def clean_backup_for_summary(backup_data: Dict[str, Any], keep_recent: int = 10) -> Dict[str, Any]:
    """
    Data refinement for summary generation

    Significantly reduced context size by preserving only the most recent N messages:
    - Fully preserve only the most recent N messages
    - Completely remove the rest
    - Compressed from 5MB to tens of KB (over 99% reduction)

    Args:
        backup_data: Original backup data
        keep_recent: Number of recent messages to fully preserve

    Returns:
        Refined backup data
    """
    messages = backup_data.get('conversation', [])
    if not messages:
        return backup_data

    total_messages = len(messages)
    cleaned_messages = messages[-keep_recent:] if total_messages > keep_recent else messages

    cleaned_backup = {
        'backup_metadata': backup_data.get('backup_metadata', {}),
        'conversation': cleaned_messages,
        'file_history': {'snapshots': []},
        'statistics': backup_data.get('statistics', {})
    }

    return cleaned_backup


def format_conversation_for_claude(messages: List[Dict[str, Any]]) -> str:
    """Formatting dialogue to be passed to Claude CLI"""
    formatted = []

    for msg in messages:
        msg_type = msg.get('type')
        timestamp = msg.get('timestamp', '')

        if msg_type == 'user':
            content = msg.get('content', '')
            if isinstance(content, str) and content.strip():
                formatted.append(f"[User - {timestamp}]\n{content}\n")

        elif msg_type == 'assistant':
            content = msg.get('content', [])
            text_parts = []

            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif item.get('type') == 'tool_use':
                            tool_name = item.get('name', '')
                            tool_input = item.get('input', {})
                            text_parts.append(f"[Tool: {tool_name}]\n{tool_input}")

            if text_parts:
                text = '\n'.join(text_parts)
                formatted.append(f"[Assistant - {timestamp}]\n{text}\n")

    return '\n---\n'.join(formatted)


def generate_claude_cli_summary(
    backup_data: Dict[str, Any],
    config: Dict[str, Any]
) -> Optional[str]:
    """
    Intelligent Summary Generation Using Claude Code CLI (with Haiku 4.5 Model)

    Fast and cost-effective summary generation using Claude Haiku 4.5:
    - Speed: Over twice as fast as Sonnet 4
    - Cost: One-third the cost of Sonnet 4 ($1/$5 per million tokens)
    - Performance: Similar coding performance to Sonnet 4

    Args:
        backup_data: Backed-up conversation data
        config: Settings

    Returns:
        Summary string or None (on failure)
    """
    strategy = config['compact_strategy']
    keep_recent = strategy.get('keep_recent_messages', 10)

    cleaned_backup = clean_backup_for_summary(backup_data, keep_recent=keep_recent)

    messages = cleaned_backup.get('conversation', [])
    if not messages:
        return None

    metadata = backup_data.get('backup_metadata', {})
    statistics = backup_data.get('statistics', {})
    focus_areas = strategy.get('focus_areas', ['Work', 'Decision Items', 'Code modification'])

    conversation_text = format_conversation_for_claude(messages)

    prompt = f"""Please summarize the next development session **concise within 5000 characters**.

## Session Information
[{focus_areas}] | Session: {metadata.get('session_id', 'N/A')[:8]}... | Branch: {metadata.get('git_branch', 'N/A')} | Messages: {statistics.get('total_messages', 0)} | Duration: {statistics.get('conversation_duration_seconds', 0)//60} minutes

## Summary Rules (Important!)
1. **Must be within 5000 characters** - Focus on bullet points, keep concise
2. Core only: Purpose of work → Key changes → Decisions made → Unfinished items
3. Code: Only filename:line (Minimize code blocks)
4. Remove unnecessary explanations, repetition, and background information

## Summary Format
# Previous Session Summary (Working Directory: {metadata.get('cwd', 'N/A')})

## Purpose of Work
[Core objective in 1-2 lines]

## Key Changes
- File name: Line - [Change details in 1 line]

## Key Decisions
- [Decision in 1 line]

## Unfinished/Next Steps
- [TODO items]

---

## Conversation Details
{conversation_text}

Summarize the key points of the above conversation within 5,000 characters. Remove unnecessary explanations and retain only the information needed to restore the work context."""

    try:
        console.print("[cyan]AI[/] Generating a quick summary with Claude Haiku 4.5...")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            temp_file = f.name

        # Run Claude CLI (print mode with JSON output)
        # Use empty configuration file and strict mode to disable MCP server
        # Double speed and reduce cost by one-third with Haiku 4.5 model
        empty_mcp_config = Path(__file__).parent.parent / "config" / "empty-mcp-config.json"
        cmd = [
            'claude',
            '-p',  # print mode
            '--model', 'claude-haiku-4-5',
            '--mcp-config', str(empty_mcp_config),
            '--strict-mcp-config',
            '--dangerously-skip-permissions',
            '--output-format', 'json'
        ]

        with open(temp_file, 'r', encoding='utf-8') as prompt_file:
            result = subprocess.run(
                cmd,
                stdin=prompt_file,
                capture_output=True,
                text=True,
                timeout=180
            )

        Path(temp_file).unlink(missing_ok=True)

        if result.returncode != 0:
            console.print(f"[yellow]WARNING: Claude CLI execution failed (exit code: {result.returncode})[/]")
            console.print(f"   stderr: {result.stderr[:500]}")
            console.print(f"   stdout: {result.stdout[:500]}")
            return None

        try:
            output_data = json.loads(result.stdout)
            summary = ""

            if isinstance(output_data, list):
                for item in output_data:
                    if isinstance(item, dict) and item.get('type') == 'result':
                        summary = item.get('result', '')
                        break

                if not summary:
                    for item in output_data:
                        if isinstance(item, dict) and item.get('type') == 'assistant':
                            message = item.get('message', {})
                            content = message.get('content', [])
                            if isinstance(content, list):
                                for content_item in content:
                                    if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                        summary = content_item.get('text', '')
                                        break
                            break
            elif isinstance(output_data, dict):
                summary = output_data.get('result', '')
                if not summary:
                    summary = output_data.get('content', '')
                    if isinstance(summary, list):
                        text_parts = []
                        for item in summary:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                        summary = '\n'.join(text_parts)
            else:
                summary = str(output_data)

            if summary and len(summary.strip()) > 0:
                console.print("[green]OK[/] Claude CLI Summary Generation Complete")
                return summary.strip()
            else:
                console.print("[yellow]WARNING: The Claude CLI response is empty.[/]")
                console.print(f"   output_data type: {type(output_data)}")
                console.print(f"   output_data preview: {str(output_data)[:500]}")
                return None

        except json.JSONDecodeError:
            if result.stdout.strip():
                console.print("[green]OK[/] Claude CLI Summary Generation Complete (text mode)")
                return result.stdout.strip()
            return None

    except subprocess.TimeoutExpired:
        console.print("[yellow]WARNING: Claude CLI execution timeout[/]")
        Path(temp_file).unlink(missing_ok=True)
        return None
    except FileNotFoundError:
        console.print("[yellow]WARNING: Claude CLI cannot be found. Ensure the 'claude' command is in your PATH.[/]")
        return None
    except Exception as e:
        console.print(f"[yellow]WARNING: Error during Claude CLI execution: {e}[/]")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def save_to_chromadb_direct(
    summary: str,
    backup_data: Dict[str, Any],
    config: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Saving to ChromaDB via MCP

    Calls the claude CLI as a subprocess to save via the MCP chromadb server
    More stable and faster than direct access via the Python client

    Args:
        summary: Summary
        backup_data: Backup data
        config: Settings

    Returns:
        (Success status, error message) tuple. True, None on success; False, "error details" on failure.
    """
    metadata = backup_data.get('backup_metadata', {})
    statistics = backup_data.get('statistics', {})

    doc_id = f"context_compact_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Get metadata template from chromadb_integration config
    chromadb_config = config['chromadb_integration']
    collection_name = chromadb_config['collection']
    metadata_template = chromadb_config['metadata_template']

    # Build doc_metadata from template, filling in dynamic values
    doc_metadata = {
        "project": metadata_template.get('project', 'example_project'),
        "subproject": metadata_template.get('subproject', 'core'),
        "type": metadata_template.get('type', 'context_compact'),
        "date": datetime.now().strftime('%Y-%m-%d'),
        "summary": f"Context compression - {statistics.get('total_messages', 0)} messages",
        "tags": metadata_template.get('tags', 'auto-compact, summary'),
        "status": metadata_template.get('status', 'completed'),
        # Additional dynamic fields
        "original_message_count": statistics.get('total_messages', 0),
        "total_tokens": statistics.get('total_tokens', 0),
        "session_id": metadata.get('session_id', ''),
        "git_branch": metadata.get('git_branch', '') or 'unknown',
        "timestamp": metadata.get('timestamp', '')
    }

    try:
        console.print(f"\n[cyan]SAVE[/] Saving to ChromaDB via MCP...")
        console.print(f"   Collection: {collection_name}")
        console.print(f"   Document ID: {doc_id}")

        project_root = find_project_root()
        if not project_root:
            return False, "Project root cannot be found"

        mcp_config = project_root / ".claude" / "config" / "chromadb-only-mcp-config.json"
        if not mcp_config.exists():
            return False, f"The MCP configuration file is missing.: {mcp_config}"

        mcp_request = {
            "collection_name": collection_name,
            "documents": [summary],
            "ids": [doc_id],
            "metadatas": [doc_metadata]
        }

        cmd = [
            "claude",
            "-p",
            '--model', 'claude-haiku-4-5',
            "--mcp-config", str(mcp_config),
            "--strict-mcp-config",
            "--dangerously-skip-permissions",
            "--output-format", "json",
            f"Add documents to Chromadb. Use the chroma_add_documents tool.: {json.dumps(mcp_request, ensure_ascii=False)}"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False
        )

        if result.returncode != 0:
            error_detail = f"MCP call failed (exit code: {result.returncode})\nstderr: {result.stderr[:200]}"
            console.print(f"   [yellow]WARNING: {error_detail}[/]")
            return False, error_detail

        try:
            output = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            output = {"raw": result.stdout}

        console.print(f"   [green]OK[/] ChromaDB saved successfully!")
        console.print(f"   Message: {statistics.get('total_messages', 0)}")
        console.print(f"   Token: {statistics.get('total_tokens', 0):,}")
        console.print(f"   Length: {len(summary)}\n")

        return True, None

    except subprocess.TimeoutExpired:
        error_detail = "MCP Call Timeout (Exceeded 120 seconds)"
        console.print(f"   [yellow]WARNING: {error_detail}[/]")
        return False, error_detail
    except Exception as e:
        error_detail = f"ChromaDB storage failure: {str(e)}"
        console.print(f"   [yellow]WARNING: {error_detail}[/]")
        traceback.print_exc(file=sys.stderr)
        return False, error_detail


def save_summary_to_chromadb(
    summary: str,
    backup_data: Dict[str, Any],
    config: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Save summary to ChromaDB (using Python client directly)
    Wrapper function maintained for legacy compatibility

    Args:
        summary: Summary
        backup_data: Backup data
        config: Settings

    Returns:
        (Success status, error message) tuple
    """
    return save_to_chromadb_direct(summary, backup_data, config)


def create_pid_file() -> Optional[Path]:
    """
    Create PID file for background process tracking

    Returns:
        Path to PID file or None if failed
    """
    try:
        project_root = find_project_root()
        if project_root:
            pid_file = project_root / ".claude" / "recovery" / "auto-compact.pid"
        else:
            pid_file = Path(".claude/recovery/auto-compact.pid")

        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()), encoding='utf-8')
        return pid_file
    except Exception as e:
        console.print(f"[yellow]⚠ Failed to create PID file: {e}[/yellow]")
        return None


def remove_pid_file() -> None:
    """Remove PID file"""
    try:
        project_root = find_project_root()
        if project_root:
            pid_file = project_root / ".claude" / "recovery" / "auto-compact.pid"
        else:
            pid_file = Path(".claude/recovery/auto-compact.pid")

        if pid_file.exists():
            pid_file.unlink()
    except Exception as e:
        console.print(f"[yellow]⚠ Failed to delete PID file: {e}[/yellow]")


def update_progress_status(
    status: str,
    stage: str,
    progress: int,
    message: str,
    error: Optional[str] = None,
    started_at: Optional[str] = None
) -> None:
    """
    Update progress status file for PostToolUse hook monitoring

    Args:
        status: running|completed|error
        stage: backup|summary|chromadb|cleanup
        progress: 0-100
        message: Current operation description
        error: Error message if status is error
        started_at: ISO timestamp when started (for first call)
    """
    try:
        project_root = find_project_root()
        if project_root:
            status_file = project_root / ".claude" / "recovery" / "compact-status.json"
        else:
            status_file = Path(".claude/recovery/compact-status.json")

        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data to preserve started_at
        existing_started_at = started_at
        if status_file.exists() and not started_at:
            try:
                existing_data = json.loads(status_file.read_text(encoding='utf-8'))
                existing_started_at = existing_data.get('started_at')
            except Exception:
                pass

        status_data = {
            'pid': os.getpid(),
            'status': status,
            'stage': stage,
            'progress': progress,
            'message': message,
            'started_at': existing_started_at or datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat() if status == 'completed' else None,
            'error': error
        }

        status_file.write_text(json.dumps(status_data, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        console.print(f"[yellow]⚠ 진행 상태 업데이트 실패: {e}[/yellow]")


def save_compact_state(
    backup_file: Optional[Path],
    summary: str,
    config: Dict[str, Any],
    backup_data: Optional[Dict[str, Any]] = None
) -> None:
    """Compression Status Save (for Recovery) - Includes Summary"""
    recovery_config = config.get('recovery', {})

    if not recovery_config.get('save_compact_state', True):
        return

    # Use the recovery path relative to the project root
    project_root = find_project_root()
    if project_root:
        recovery_file = project_root / ".claude" / "recovery" / "compact-recovery.json"
    else:
        recovery_file = Path(recovery_config['recovery_file'])

    recovery_file.parent.mkdir(parents=True, exist_ok=True)

    state: Dict[str, Any] = {
        'timestamp': datetime.now().isoformat(),
        'backup_file': str(backup_file) if backup_file else None,
        'summary': summary,
        'summary_length': len(summary) if summary else 0,
        'collection': config['chromadb_integration']['collection'],
        'auto_compact_triggered': True,
        'recovered': False,
    }

    if backup_data:
        statistics = backup_data.get('statistics', {})
        state['statistics'] = {
            'total_messages': statistics.get('total_messages', 0),
            'total_tokens': statistics.get('total_tokens', 0),
            'conversation_duration': statistics.get('conversation_duration_seconds', 0)
        }

    with open(recovery_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def create_compact_marker(config: Dict[str, Any]) -> None:
    """Create a compression marker (so the recovery helper can detect it)"""
    project_root = find_project_root()
    if project_root:
        recovery_file = project_root / ".claude" / "recovery" / "compact-recovery.json"
    else:
        recovery_config = config.get('recovery', {})
        recovery_file = Path(recovery_config.get('recovery_file', '.claude/recovery/compact-recovery.json'))

    recovery_file.parent.mkdir(parents=True, exist_ok=True)

    state = {
        'timestamp': datetime.now().isoformat(),
        'auto_compact_triggered': True,
        'collection': config['chromadb_integration']['collection'],
        'message': 'Automatic context compression has occurred. Summarize the conversation and save it to ChromaDB.'
    }

    with open(recovery_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def main():
    """Main Function"""
    init_sentry('auto-compact', additional_tags={'hook_type': 'pre_compact'})

    logger = HookLogger("auto-compact")

    try:
        logger.log_start()

        add_breadcrumb("Hook execution started", category="lifecycle")

        pid_file = create_pid_file()
        if pid_file:
            add_breadcrumb("PID file created", category="progress", data={"pid": os.getpid()})
            logger.log_info("PID File Creation", pid=os.getpid(), pid_file=str(pid_file))

        start_time = datetime.now().isoformat()
        update_progress_status(
            status="running",
            stage="init",
            progress=0,
            message="Context Compression Start",
            started_at=start_time
        )

        config = load_auto_compact_config()
        add_breadcrumb("Config loaded successfully", category="config", data={"collection": config['chromadb_integration']['collection']})

        update_progress_status(
            status="running",
            stage="init",
            progress=10,
            message="Settings loaded"
        )

        conversation = ""
        try:
            if select.select([sys.stdin], [], [], 5)[0]:
                conversation = sys.stdin.read()
                logger.log_info(
                    "Reading dialogue content from stdin successful",
                    content_length=len(conversation) if conversation else 0
                )
            else:
                warning_msg = "stdin read timeout (5 seconds) - Manual compression or stdin not passed"
                console.print(f"[yellow]WARNING: {warning_msg}[/]")
                logger.log_error(warning_msg)
        except Exception as e:
            error_msg = f"stdin reading error: {e}"
            console.print(f"[yellow]WARNING: {error_msg}[/]")
            logger.log_error(error_msg)

        backup_file = None
        backup_data = None
        if conversation and conversation.strip():
            update_progress_status(
                status="running",
                stage="backup",
                progress=20,
                message="Backing up conversation content..."
            )
            add_breadcrumb("Starting backup creation", category="backup", data={"size": len(conversation)})
            backup_file, backup_data = backup_conversation(conversation, config)
            if backup_file:
                stats = backup_data.get('statistics', {}) if backup_data else {}
                add_breadcrumb("Backup created successfully", category="backup", data={
                    "file": str(backup_file),
                    "messages": stats.get('total_messages', 0),
                    "tokens": stats.get('total_tokens', 0)
                })
                logger.log_info(
                    "Backup file creation complete",
                    backup_file=str(backup_file),
                    total_messages=stats.get('total_messages', 0),
                    total_tokens=stats.get('total_tokens', 0)
                )
                update_progress_status(
                    status="running",
                    stage="backup",
                    progress=40,
                    message=f"Backup complete ({stats.get('total_messages', 0)} messages)"
                )
        else:
            warning_msg = "Conversation content not delivered - either manually compressed or empty conversation"
            add_breadcrumb(warning_msg, category="backup", level="warning")
            logger.log_error(warning_msg)

        create_compact_marker(config)
        add_breadcrumb("Compact marker created", category="marker")
        logger.log_info("압축 마커 생성 완료")

        summary = ""
        if backup_data:
            update_progress_status(
                status="running",
                stage="summary",
                progress=50,
                message="Generating a summary using Claude CLI..."
            )
            add_breadcrumb("Starting summary generation", category="summary")
            summary = generate_claude_cli_summary(backup_data, config)

            if summary:
                add_breadcrumb("Summary generated successfully", category="summary", data={"length": len(summary)})
                logger.log_info("Summary generation complete", summary_length=len(summary))
                update_progress_status(
                    status="running",
                    stage="summary",
                    progress=70,
                    message=f"Summary generation complete ({len(summary)})"
                )

                update_progress_status(
                    status="running",
                    stage="chromadb",
                    progress=80,
                    message="Saving to ChromaDB..."
                )
                add_breadcrumb("Saving to ChromaDB", category="chromadb")
                success, error_msg = save_summary_to_chromadb(summary, backup_data, config)

                if success:
                    add_breadcrumb("ChromaDB save successful", category="chromadb")
                    logger.log_info("ChromaDB saved successfully")
                    update_progress_status(
                        status="running",
                        stage="chromadb",
                        progress=90,
                        message="ChromaDB saved successfully"
                    )
                else:
                    add_breadcrumb("ChromaDB save failed", category="chromadb", level="error",
                                 data={"error": error_msg})
                    logger.log_error(f"ChromaDB storage failure: {error_msg}")

                    capture_exception(
                        Exception(f"ChromaDB save failed: {error_msg}"),
                        context={
                            "error_detail": error_msg,
                            "collection": config['chromadb_integration']['collection'],
                            "summary_length": len(summary),
                            "message_count": backup_data.get('statistics', {}).get('total_messages', 0)
                        }
                    )
            else:
                add_breadcrumb("Summary generation failed", category="summary", level="error")
                logger.log_error("Summary generation failed")
        else:
            logger.log_error("No backup data")

        if backup_file:
            update_progress_status(
                status="running",
                stage="cleanup",
                progress=95,
                message="Saving compressed state..."
            )
            save_compact_state(backup_file, summary, config, backup_data)
            add_breadcrumb("Compact state saved", category="state")
            logger.log_info("Compression state saved successfully")

        update_progress_status(
            status="completed",
            stage="cleanup",
            progress=100,
            message="Context compression complete"
        )

        remove_pid_file()
        add_breadcrumb("PID file removed", category="progress")
        logger.log_info("PID file deletion complete")

        logger.log_end(
            success=True,
            backup_created=bool(backup_file),
            summary_generated=bool(summary)
        )

        # Sentry flush before exit
        flush()
        sys.exit(0)

    except Exception as e:
        error_msg = f"Error occurred: {e}"
        console.print(f"[red]ERROR: {error_msg}[/]")
        traceback.print_exc(file=sys.stderr)

        update_progress_status(
            status="error",
            stage="error",
            progress=0,
            message="Context compression failed",
            error=error_msg
        )

        remove_pid_file()

        # Capture exception to Sentry
        capture_exception(e, context={
            "hook": "auto-compact",
            "error_message": error_msg
        })

        logger.log_end(success=False, error=str(e))

        # Flush Sentry before exit
        flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
