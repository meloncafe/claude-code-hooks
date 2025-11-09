#!/usr/bin/env python3
"""
Post Tool Use Hook: Auto-Compact Progress Display
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def find_project_root() -> Optional[Path]:
    """
    Example Project Automatically detects project root
    Finds the root directory containing `pyproject.toml`
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


def get_pid_file() -> Optional[Path]:
    """Get PID file path"""
    project_root = find_project_root()
    if project_root:
        return project_root / ".claude" / "recovery" / "auto-compact.pid"
    return Path(".claude/recovery/auto-compact.pid")


def get_status_file() -> Optional[Path]:
    """Get status file path"""
    project_root = find_project_root()
    if project_root:
        return project_root / ".claude" / "recovery" / "compact-status.json"
    return Path(".claude/recovery/compact-status.json")


def is_process_running(pid: int) -> bool:
    """
    Check if process with given PID is running

    Args:
        pid: Process ID to check

    Returns:
        True if process is running, False otherwise
    """
    try:
        # os.kill(pid, 0) doesn't kill the process, just checks if it exists
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def load_status() -> Optional[Dict[str, Any]]:
    """
    Load progress status from file

    Returns:
        Status dict or None if not found or error
    """
    try:
        status_file = get_status_file()
        if not status_file or not status_file.exists():
            return None

        status_data = json.loads(status_file.read_text(encoding='utf-8'))
        return status_data
    except Exception:
        return None


def cleanup_stale_files() -> None:
    """Clean up PID and status files if process is not running"""
    try:
        pid_file = get_pid_file()
        status_file = get_status_file()

        if pid_file and pid_file.exists():
            pid_file.unlink()

        if status_file and status_file.exists():
            status_file.unlink()
    except Exception:
        pass


def display_progress(status: Dict[str, Any]) -> None:
    """
    Display progress status to stderr

    Args:
        status: Status dict with progress info
    """
    status_type = status.get('status', 'unknown')
    stage = status.get('stage', 'unknown')
    progress = status.get('progress', 0)
    message = status.get('message', '')
    pid = status.get('pid')

    # Check if process is still running (only for 'running' status)
    if status_type == 'running' and pid and not is_process_running(pid):
        # Process not running but status file exists - clean up
        cleanup_stale_files()
        return

    if status_type == 'running':
        # Running: show brief progress
        progress_bar = "=" * (progress // 5) + ">" + "." * (20 - progress // 5)
        sys.stderr.write(f"\r🔄 Context compression in progress... [{progress_bar}] {progress}% - {message}")
        sys.stderr.flush()

    elif status_type == 'completed':
        # Completed: show completion message and cleanup
        msg = "\n" + "="*70 + "\n"
        msg += "✅ Context compression complete\n"
        msg += "="*70 + "\n"
        msg += "When you start the next session, you will see a condensed summary.\n"
        msg += "To end the current session, use /clear or start a new session.\n"
        msg += "="*70 + "\n\n"

        # Output to both stdout and stderr for visibility
        sys.stdout.write(msg)
        sys.stdout.flush()
        sys.stderr.write(msg)
        sys.stderr.flush()

        # Clean up status file (process already removed PID file)
        cleanup_stale_files()

    elif status_type == 'error':
        # Error: show error message
        error = status.get('error', 'Unknown error')
        msg = "\n" + "="*70 + "\n"
        msg += "❌ Context compression failed\n"
        msg += "="*70 + "\n"
        msg += f"Error: {error}\n"
        msg += "Check the log.: .claude/logs/hooks/auto-compact.log\n"
        msg += "="*70 + "\n\n"

        # Output to both stdout and stderr for visibility
        sys.stdout.write(msg)
        sys.stdout.flush()
        sys.stderr.write(msg)
        sys.stderr.flush()

        # Clean up
        cleanup_stale_files()


def main():
    """Main entry point"""
    try:
        # Load status
        status = load_status()

        if not status:
            # No status file - nothing to display
            return

        # Display progress
        display_progress(status)

    except Exception:
        # Silent fail - don't interfere with user's workflow
        pass


if __name__ == "__main__":
    main()
