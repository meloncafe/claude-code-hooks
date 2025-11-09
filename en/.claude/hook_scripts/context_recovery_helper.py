#!/usr/bin/env python3
"""
Example Project Context Recovery Helper

Automatically restore compressed context:
1. Load saved summaries from recovery state files
2. If no summary exists, automatically load the most recent backup file
3. Generate intelligent summaries using Claude Code CLI (if needed)
4. Automatically provide context to new sessions
5. Save to ChromaDB (optional)
"""

import gzip
import json
import os
import signal
import subprocess
import sys
import tempfile
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from common.logger import HookLogger
from common.sentry import init_sentry, capture_exception, add_breadcrumb, flush
from common.config import load_config
from common.formatting import console

# token_manager import 추가
from token_manager import is_continued_session

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box


def find_project_root() -> Optional[Path]:
    """
    Example Project Automatically detects project root
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


def load_recovery_state() -> Optional[Dict[str, Any]]:
    """Load Recovery State File"""
    project_root = find_project_root()

    candidates = []

    if project_root:
        candidates.append(project_root / ".claude" / "recovery" / "compact-recovery.json")

    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        candidates.append(Path(project_dir) / ".claude" / "recovery" / "compact-recovery.json")

    candidates.extend([
        Path.cwd() / ".claude" / "recovery" / "compact-recovery.json",
        Path.home() / ".claude" / "recovery" / "compact-recovery.json",
    ])

    for candidate in candidates:
        if candidate.exists():
            with open(candidate, 'r', encoding='utf-8') as f:
                return json.load(f)

    return None


def save_recovery_state(state: Dict[str, Any]) -> None:
    """
    Save Recovery State File

    Args:
        state: State data to save
    """
    project_root = find_project_root()

    if project_root:
        recovery_file = project_root / ".claude" / "recovery" / "compact-recovery.json"
    else:
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
        if project_dir:
            recovery_file = Path(project_dir) / ".claude" / "recovery" / "compact-recovery.json"
        else:
            recovery_file = Path.cwd() / ".claude" / "recovery" / "compact-recovery.json"

    recovery_file.parent.mkdir(parents=True, exist_ok=True)

    with open(recovery_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def list_backups() -> List[tuple[Path, datetime]]:
    """Backup File List Inquiry (Includes JSON, gzip, and txt files)"""
    project_root = find_project_root()

    backup_dirs = []

    if project_root:
        backup_dirs.append(project_root / ".claude" / "backups")

    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        backup_dirs.append(Path(project_dir) / ".claude" / "backups")

    backup_dirs.extend([
        Path.cwd() / ".claude" / "backups",
        Path.home() / ".claude" / "backups",
    ])

    backups = []
    seen_files = set()
    for backup_dir in backup_dirs:
        if not backup_dir.exists():
            continue

        patterns = ['conversation_*.json', 'conversation_*.json.gz', 'conversation_*.txt']
        for pattern in patterns:
            for backup_file in backup_dir.glob(pattern):
                abs_path = backup_file.resolve()
                if abs_path in seen_files:
                    continue
                seen_files.add(abs_path)

                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append((backup_file, mtime))

    return sorted(backups, key=lambda x: x[1], reverse=True)


def load_backup_file(backup_path: Path) -> Optional[Dict[str, Any]]:
    """Load Backup File (JSON or gzip)"""
    try:
        if backup_path.suffix == '.gz':
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:  # type: ignore[assignment]
                return json.load(f)
        elif backup_path.suffix == '.json':
            with open(backup_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return None
    except Exception as e:
        console.print(f"[yellow]WARNING: Failed to load backup file: {e}[/]")
        return None


def load_summary_from_state(state: Dict[str, Any]) -> Optional[str]:
    """
    Load saved summary from recovery state file

    Args:
        state: Recovery state data

    Returns:
        Saved summary or None
    """
    summary = state.get('summary', '')
    if summary and isinstance(summary, str) and len(summary.strip()) > 0:
        return summary.strip()
    return None


def print_recovery_guide(recovery_state: Optional[Dict[str, Any]], collection: str) -> None:
    """Context Recovery Guide Output"""
    guide_parts = []

    if recovery_state:
        timestamp = recovery_state.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                guide_parts.append(f"[cyan]Last compression time:[/] {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except (ValueError, AttributeError):
                pass

        backup_file = recovery_state.get('backup_file')
        if backup_file:
            guide_parts.append(f"[cyan]Backup file:[/] {backup_file}")

    guide_parts.append(f"[cyan]ChromaDB Collection:[/] {collection}\n")

    # 방법 1
    guide_parts.append("[bold yellow][Method 1] Searching for Compressed Contexts in ChromaDB[/]\n")
    guide_parts.append(f"""chroma:chroma_query_documents(
    collection_name="{collection}",
    query_texts=["Context Compression Summary"],
    n_results=5,
    where={{"type": "context_compact"}}
)\n""")

    # 방법 2
    guide_parts.append("[bold yellow][Method 2] Restore from Backup File[/]\n")

    backups = list_backups()
    if backups:
        guide_parts.append("[cyan]Recent backup files:[/]")
        for i, (backup_path, mtime) in enumerate(backups[:5], 1):
            size = backup_path.stat().st_size
            guide_parts.append(f"   {i}. {backup_path.name}")
            guide_parts.append(f"      Time: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            guide_parts.append(f"      Size: {size:,} bytes")
            guide_parts.append(f"      Path: {backup_path}\n")
    else:
        guide_parts.append("   [yellow]WARNING: The backup file cannot be found.[/]\n")

    # 방법 3
    guide_parts.append("[bold yellow][Method 3] Manual Recovery[/]\n")
    guide_parts.append("Provide the contents of the backup file to the new conversation as follows::")
    guide_parts.append('   "The following is the context from the previous conversation: [Backup content]"\n')

    guide_parts.append("[dim]Tip: To prevent compression, edit the .claude/config/auto-compact.json file.")
    guide_parts.append("     Set enabled to false or increase the threshold.[/]")

    console.print(Panel(
        "\n".join(guide_parts),
        title="[bold white]Context Recovery Guide[/]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    ))


def check_recent_compacts(config: Dict[str, Any], days: int = 7) -> None:
    """Recent Compression History"""
    collection = config.get('collection', 'example_project_context')

    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    query = f"""chroma:chroma_query_documents(
    collection_name="{collection}",
    query_texts=["Context compression"],
    n_results=20,
    where={{
        "type": "context_compact",
        "date": {{"$gte": "{start_date}"}}
    }}
)"""

    content = f"[bold cyan]ChromaDB Query:[/]\n{query}\n\n[dim]Tip: This query allows you to view all recently compressed contexts.[/]"

    console.print(Panel(
        content,
        title=f"[bold white]View compressed history for the last {days} days[/]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    ))


def list_recovery_files() -> None:
    """Verify Recovery-Related Files"""
    project_root = find_project_root()

    files = [
        (".claude/recovery/compact-recovery.json", "Recovery Status File"),
        (".claude/recovery/recovery-instructions.md", "Recovery Guidelines Document"),
        (".claude/backups/", "Backup directory"),
    ]

    table = Table(
        title="Recovery-related files",
        show_header=True,
        header_style="bold cyan",
        box=box.SIMPLE
    )

    table.add_column("Status", style="cyan", justify="center")
    table.add_column("File", style="white")
    table.add_column("Explanation", style="dim")
    table.add_column("Information", style="yellow")

    for filepath, description in files:
        if project_root:
            full_path = project_root / filepath
        else:
            full_path = Path.cwd() / filepath

        if full_path.exists():
            if full_path.is_file():
                size = full_path.stat().st_size
                mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
                info = f"Size: {size:,} bytes\nRevision: {mtime.strftime('%Y-%m-%d %H:%M:%S')}"
                table.add_row("[green]Existence[/]", str(filepath), description, info)
            else:
                table.add_row("[green]Existence[/]", str(filepath), description, "Directory")
        else:
            table.add_row("[red]None[/]", str(filepath), description, "-")

    console.print(table)


def check_recent_compact(state: Optional[Dict[str, Any]], threshold_hours: int = 24) -> bool:
    """
    Check if automatic compaction has occurred recently

    Args:
        state: Recovery state data
        threshold_hours: Threshold for displaying recovery messages (in hours, default 24 hours)

    Returns:
        Whether recent compaction occurred
    """
    if not state:
        return False

    if state.get('recovered', False):
        return False

    timestamp_str = state.get('timestamp', '')
    if not timestamp_str:
        return False

    try:
        compact_time = datetime.fromisoformat(timestamp_str)

        if compact_time.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now()

        diff = now - compact_time
        return diff.total_seconds() < (threshold_hours * 3600)
    except Exception:
        return False


def print_quiet_status():
    """Quiet status message when no recovery is needed"""
    console.print("[green]✓[/green] Normal session start (no compression history)")


@contextmanager
def timeout_context(seconds: int):
    """
    Implementing Timeout with Context Manager

    Args:
        seconds: Timeout in seconds

    Raises:
        TimeoutError: When a timeout occurs
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f"The operation did not complete within {seconds} seconds.")

    if hasattr(signal, 'SIGALRM'):
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
    else:
        yield


def main():
    """Main Function - Automatic Context Recovery"""
    init_sentry('context-recovery-helper', additional_tags={'hook_type': 'session_start'})

    logger = HookLogger("context-recovery-helper") if HookLogger else None

    try:
        if logger:
            logger.log_start()

        add_breadcrumb("Recovery hook execution started", category="lifecycle")

        is_new_session = not is_continued_session()
        add_breadcrumb("Session continuity check", category="session", data={"is_new_session": is_new_session})

        if logger:
            logger.log_info("Session Continuity Check", is_new_session=is_new_session)

        if not is_new_session:
            if logger:
                logger.log_end(success=True, status="continued_session")
            sys.exit(0)

        config = load_config('auto-compact.json')
        add_breadcrumb("Config loaded", category="config")

        state = load_recovery_state()
        add_breadcrumb("Recovery state loaded", category="state", data={"has_state": bool(state)})

        recovery_config = config.get('recovery', {})
        threshold_hours = int(recovery_config.get('threshold_hours', 12))
        is_recent_compact = check_recent_compact(state, threshold_hours=threshold_hours)
        add_breadcrumb("Recent compact check", category="compact", data={"is_recent": is_recent_compact})

        summary = state.get('summary') if state else None
        has_summary = bool(summary and summary.strip())

        if logger:
            logger.log_info(
                "Check recovery status",
                has_state=bool(state),
                is_recent_compact=is_recent_compact,
                has_summary=has_summary
            )

        if not state or not is_recent_compact:
            if logger:
                logger.log_end(success=True, status="no_recent_compact")
            sys.exit(0)

        add_breadcrumb("Attempting to load summary from state", category="recovery")
        summary = load_summary_from_state(state)

        if not summary:
            console.print("[yellow]WARNING: There is no summary in the compressed file.[/]")
            console.print("[yellow]A summary will be generated again in the next session.[/]")
            print_quiet_status()
            if logger:
                logger.log_end(success=False, status="no_summary_in_state")
            flush()
            sys.exit(0)

        add_breadcrumb("Summary output", category="recovery", data={"length": len(summary)})

        console.print("\n" + "="*80)
        console.print("[bold yellow]IMPORTANT: The summary below is the official context for this session.[/bold yellow]")
        console.print("[bold yellow]Prioritize the content below over Claude's auto-generated summaries.[/bold yellow]")
        console.print("="*80 + "\n")

        console.print(f"\n{summary}\n")

        console.print("[green]✓[/green] Restoration complete\n")

        state['recovered'] = True
        state['recovered_at'] = datetime.now().isoformat()
        save_recovery_state(state)

        add_breadcrumb("Recovery completed successfully", category="recovery")

        if logger:
            logger.log_end(success=True, status="recovery_completed", summary_length=len(summary))

        flush()
        sys.exit(0)

    except Exception as e:
        error_msg = f"Recovery Helper Error During Execution: {e}"
        console.print(f"[yellow]WARNING: {error_msg}[/]")
        console.print("Continue the session....\n")
        traceback.print_exc(file=sys.stderr)

        # Capture exception to Sentry
        capture_exception(e, context={
            "hook": "context-recovery-helper",
            "error_message": error_msg
        })

        if logger:
            logger.log_end(success=False, error=error_msg)

        flush()
        sys.exit(0)


if __name__ == "__main__":
    main()
