#!/usr/bin/env python3
"""
Claude Code Token Management CLI

Unified token management utility for Claude Code sessions.

Commands:
  extract          PostToolUse Hook - extract and update token usage
  reset            Reset token usage counters
  check-continuity Check if session is continued from previous
  status           Display current token usage status
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table
from rich import box

app = typer.Typer(
    name="token-manager",
    help="Token management utilities for Claude Code sessions"
)
console = Console()


# ============================================================================
# Shared Utilities
# ============================================================================

def get_session_file_path() -> Optional[Path]:
    """Get current session .jsonl file path."""
    session_id = os.environ.get('CLAUDE_SESSION_ID')

    project_path = Path.cwd()
    # Remove leading / before replacing remaining / with -
    path_str = str(project_path)
    if path_str.startswith('/'):
        path_str = path_str[1:]
    safe_path = '-' + path_str.replace('/', '-')
    session_dir = Path.home() / '.claude' / 'projects' / safe_path

    if session_id:
        session_file = session_dir / f'{session_id}.jsonl'
        return session_file if session_file.exists() else None

    # Fallback: most recent session file
    if not session_dir.exists():
        return None

    try:
        session_files = list(session_dir.glob('*.jsonl'))
        if not session_files:
            return None
        session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return session_files[0]
    except Exception:
        return None


def load_token_usage() -> Dict[str, Any]:
    """Load token-usage.json."""
    config_path = Path.home() / '.claude' / 'sessions' / 'token-usage.json'

    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return {
            "current_session": "",
            "sessions": {},
            "total_accumulated": 0,
            "last_reset": datetime.now(timezone.utc).isoformat(),
            "reset_count": 0
        }

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception:
        return {
            "current_session": "",
            "sessions": {},
            "total_accumulated": 0,
            "last_reset": datetime.now(timezone.utc).isoformat(),
            "reset_count": 0
        }


def save_token_usage(data: Dict[str, Any]) -> bool:
    """Save token-usage.json."""
    config_path = Path.home() / '.claude' / 'sessions' / 'token-usage.json'

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        console.print(f"[red]Error saving token-usage.json: {e}[/red]")
        return False


def load_token_limits() -> Dict[str, Any]:
    """
    Load token-limits.json and auto-configure auto_stop from ~/.claude.json autoCompactEnabled.

    Logic:
    - autoCompactEnabled=true → session auto_stop=true, total auto_stop=false
    - autoCompactEnabled=false → session auto_stop=false, total auto_stop=true
    """
    config_path = Path('.claude/config/token-limits.json')

    # Auto-detect Claude Code auto compact setting
    auto_compact_enabled = False
    try:
        claude_config_path = Path.home() / '.claude.json'
        if claude_config_path.exists():
            with open(claude_config_path, 'r') as f:
                claude_config = json.load(f)
                auto_compact_enabled = claude_config.get('autoCompactEnabled', False)
    except Exception:
        pass

    defaults = {
        "enabled": True,
        "session_limits": {
            "warning": 150000,
            "critical": 180000,
            "auto_stop": not auto_compact_enabled  # false면 세션 체크
        },
        "total_limits": {
            "warning": 400000,
            "critical": 500000,
            "auto_stop": auto_compact_enabled  # true면 전체 체크
        },
        "display": {
            "show_on_startup": False,
            "show_on_normal": False,
            "show_on_warning": True,
            "show_on_critical": True,
            "progress_bar": True,
            "format": "minimal"
        },
        "auto_reset": {"enabled": True, "threshold": 500000}
    }

    if not config_path.exists():
        limits = defaults
    else:
        try:
            with open(config_path, 'r') as f:
                limits = json.load(f)
                # Auto-configure auto_stop
                limits.setdefault('session_limits', {})['auto_stop'] = not auto_compact_enabled
                limits.setdefault('total_limits', {})['auto_stop'] = auto_compact_enabled
        except Exception:
            limits = defaults

    return limits


# ============================================================================
# Command: extract (PostToolUse Hook)
# ============================================================================

def extract_token_usage_from_line(line: str) -> Optional[Dict[str, int]]:
    """Extract token usage from JSONL line."""
    try:
        data = json.loads(line)
        if data.get('type') != 'assistant':
            return None

        message = data.get('message', {})
        usage = message.get('usage')
        if not usage:
            return None

        input_tokens = usage.get('input_tokens', 0)
        cache_read_tokens = usage.get('cache_read_input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)

        total_input = input_tokens + cache_read_tokens
        total_tokens = total_input + output_tokens

        return {
            'input_tokens': input_tokens,
            'cache_read_tokens': cache_read_tokens,
            'total_input_tokens': total_input,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def get_latest_token_usage() -> Optional[Dict[str, int]]:
    """Get latest token usage from session file."""
    session_file = get_session_file_path()
    if not session_file:
        return None

    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Check all lines in reverse order to find latest token usage
        for line in reversed(lines):
            usage = extract_token_usage_from_line(line)
            if usage:
                return usage
        return None
    except (OSError, IOError):
        return None


def update_token_usage(current_tokens: int) -> Dict[str, Any]:
    """Update token usage and return updated data."""
    usage_data = load_token_usage()

    session_file = get_session_file_path()
    if not session_file:
        return usage_data

    current_session_id = session_file.stem

    # Detect session transition
    old_session_id = usage_data.get('current_session', '')
    if old_session_id and old_session_id != current_session_id:
        if old_session_id in usage_data.get('sessions', {}):
            old_tokens = usage_data['sessions'][old_session_id].get('tokens', 0)
            usage_data['sessions'][old_session_id]['status'] = 'compacted'
            usage_data['total_accumulated'] = usage_data.get('total_accumulated', 0) + old_tokens

    # Update current session
    usage_data['current_session'] = current_session_id

    if 'sessions' not in usage_data:
        usage_data['sessions'] = {}

    usage_data['sessions'][current_session_id] = {
        'tokens': current_tokens,
        'updated': datetime.now(timezone.utc).isoformat(),
        'status': 'active'
    }

    save_token_usage(usage_data)
    return usage_data


def check_limits_and_warn(current_tokens: int, total_tokens: int, limits: Dict[str, Any]) -> bool:
    """Check thresholds and display warnings. Returns True if auto_stop triggered."""
    if not limits.get('enabled', True):
        return False

    session_limits = limits.get('session_limits', {})
    total_limits = limits.get('total_limits', {})
    display = limits.get('display', {})
    format_type = display.get('format', 'minimal')

    # Auto-detect which limit to use based on auto_stop settings
    session_auto_stop = session_limits.get('auto_stop', False)
    total_auto_stop = total_limits.get('auto_stop', False)

    should_stop = False

    # Determine primary check based on auto_stop (set by autoCompactEnabled)
    if session_auto_stop:
        # Session auto_stop enabled (autoCompactEnabled=false → session persists)
        check_value = current_tokens
        check_limits = session_limits
        check_type = "session"
        critical_threshold = session_limits.get('critical', 180000)
        warning_threshold = session_limits.get('warning', 150000)
    else:
        # Total auto_stop enabled (autoCompactEnabled=true → sessions reset often)
        check_value = total_tokens
        check_limits = total_limits
        check_type = "total"
        critical_threshold = total_limits.get('critical', 500000)
        warning_threshold = total_limits.get('warning', 400000)

    # Determine state
    state = 'normal'
    if check_value >= critical_threshold:
        state = 'critical'
    elif check_value >= warning_threshold:
        state = 'warning'

    # Legacy: Also check the other metric for informational purposes
    # Session token check (for display only if not primary)
    session_critical = session_limits.get('critical', 130000)
    session_warning = session_limits.get('warning', 100000)

    session_state = 'normal'
    if current_tokens >= session_critical:
        session_state = 'critical'
    elif current_tokens >= session_warning:
        session_state = 'warning'

    # Total token check (for display only if not primary)
    total_critical = total_limits.get('critical', 500000)
    total_warning = total_limits.get('warning', 400000)

    total_state = 'normal'
    if total_tokens >= total_critical:
        total_state = 'critical'
    elif total_tokens >= total_warning:
        total_state = 'warning'

    # Display based on primary check type and state
    if state == 'critical' and display.get('show_on_critical', True):
        if format_type == 'silent':
            pass
        elif format_type == 'minimal':
            label = "Session" if check_type == "session" else "All"
            msg = f"🚨 {label} {check_value:,}/{critical_threshold:,}"
            sys.stderr.write(f"\n{msg}\n")
            sys.stderr.flush()
        else:  # detailed
            label = "Session token" if check_type == "session" else "Total Cumulative Tokens"
            msg = f"\n🚨 CRITICAL: {label} {check_value:,} / {critical_threshold:,} excess!\n"
            sys.stderr.write(msg)
            sys.stderr.flush()
            console.print(f"[red bold]{msg.strip()}[/red bold]")

        if check_limits.get('auto_stop', False):
            console.print("[red]Work suspended (auto_stop enabled)[/red]")
            should_stop = True

    elif state == 'warning' and display.get('show_on_warning', True):
        percentage = check_value * 100 // critical_threshold
        if format_type == 'silent':
            pass
        elif format_type == 'minimal':
            label = "Session" if check_type == "session" else "All"
            msg = f"⚠️  {label} {check_value:,}/{critical_threshold:,} ({percentage}%)"
            sys.stderr.write(f"\n{msg}\n")
            sys.stderr.flush()
        else:  # detailed
            label = "Session token" if check_type == "session" else "Total Cumulative Tokens"
            msg = f"\n⚠️  WARNING: {label} {check_value:,} / {critical_threshold:,} ({percentage}%)\n"
            sys.stderr.write(msg)
            sys.stderr.flush()
            console.print(f"[yellow]{msg.strip()}[/yellow]")

    elif state == 'normal' and display.get('show_on_normal', False):
        percentage = check_value * 100 // critical_threshold
        if format_type == 'minimal':
            label = "Session" if check_type == "session" else "All"
            msg = f"✓ {label} {check_value:,}/{critical_threshold:,} ({percentage}%)"
            sys.stderr.write(f"{msg}\n")
            sys.stderr.flush()
        elif format_type == 'detailed':
            label = "Session" if check_type == "session" else "Total"
            msg = f"✓ {label}: {check_value:,}/{critical_threshold:,} ({percentage}%)"
            if format_type == 'detailed':
                # Show both metrics in detailed mode
                msg += f" | Session: {current_tokens:,} | Total: {total_tokens:,}"
            sys.stderr.write(f"{msg}\n")
            sys.stderr.flush()

    return should_stop


@app.command()
def check():
    """
    PreToolUse Hook - check token limits before execution.

    Automatically called before each tool execution to check if limits exceeded.
    """
    try:
        usage_data = load_token_usage()
        current_session_id = usage_data.get('current_session', '')
        sessions = usage_data.get('sessions', {})

        if not current_session_id or current_session_id not in sessions:
            sys.exit(0)

        session_data = sessions[current_session_id]
        current_tokens = session_data.get('tokens', 0)
        total_accumulated = usage_data.get('total_accumulated', 0) + current_tokens

        # Check thresholds
        limits = load_token_limits()
        should_stop = check_limits_and_warn(current_tokens, total_accumulated, limits)

        # If auto_stop triggered, block execution
        if should_stop:
            msg = "\n🛑 CRITICAL: Token limit exceeded - blocking operation\n"
            msg += f"   Current session: {current_tokens:,} tokens\n"
            msg += "   Please start a new session or increase limits\n\n"
            sys.stderr.write(msg)
            sys.stderr.flush()
            sys.exit(2)  # Block execution - check() only checks, doesn't save

        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Token manager error: {e}[/red]", style="dim")
        sys.exit(0)


@app.command()
def extract():
    """
    PostToolUse Hook - extract and update token usage.

    Automatically called after each tool execution to track token usage.
    """
    try:
        usage = get_latest_token_usage()

        if not usage:
            sys.exit(0)

        current_tokens = usage['total_tokens']

        # Update JSON
        usage_data = update_token_usage(current_tokens)

        # Calculate total accumulated
        total_accumulated = usage_data.get('total_accumulated', 0) + current_tokens

        # Check auto_reset threshold
        limits = load_token_limits()
        auto_reset = limits.get('auto_reset', {})
        if auto_reset.get('enabled', False):
            reset_threshold = auto_reset.get('threshold', 500000)
            if total_accumulated >= reset_threshold:
                # Reset total_accumulated
                usage_data['total_accumulated'] = 0
                usage_data['last_reset'] = datetime.now(timezone.utc).isoformat()
                usage_data['reset_count'] = usage_data.get('reset_count', 0) + 1
                save_token_usage(usage_data)
                total_accumulated = current_tokens

                # Notify user
                msg = f"\n🔄 AUTO RESET: Total accumulated tokens reset at {reset_threshold:,}\n"
                msg += f"   Reset count: {usage_data['reset_count']}\n\n"
                sys.stderr.write(msg)
                sys.stderr.flush()

        # Check thresholds and block if auto_stop triggered
        should_stop = check_limits_and_warn(current_tokens, total_accumulated, limits)

        # If auto_stop triggered, trigger compact and block execution
        if should_stop:
            # Check save_on_critical setting
            compact_triggered = False
            try:
                config_path = Path('.claude/config/auto-compact.json')
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        compact_config = json.load(f)

                    save_on_critical = compact_config.get('triggers', {}).get('save_on_critical', False)
                    auto_compact_enabled = compact_config.get('triggers', {}).get('auto_compact_on_threshold', True)

                    if save_on_critical:
                        if auto_compact_enabled:
                            # Auto-execute compact in background
                            import subprocess
                            subprocess.Popen(
                                ['python3', '.claude/hook_scripts/auto_compact.py'],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            compact_triggered = True
                            sys.stderr.write("\n" + "="*70 + "\n")
                            sys.stderr.write("🔄 CRITICAL: Automatic Context Compression Initiated\n")
                            sys.stderr.write("="*70 + "\n")
                            sys.stderr.write("Compression is running in the background....\n")
                            sys.stderr.write("After completion, use /clear or start a new session.\n")
                            sys.stderr.write("="*70 + "\n\n")
                            sys.stderr.flush()
                        else:
                            # Manual instruction
                            sys.stderr.write("\n" + "="*70 + "\n")
                            sys.stderr.write("⚠️  CRITICAL: Context save needed\n")
                            sys.stderr.write("="*70 + "\n")
                            sys.stderr.write("ACTION REQUIRED: Run the following command:\n")
                            sys.stderr.write("  python3 .claude/hook_scripts/auto_compact.py\n")
                            sys.stderr.write("After save completes, run /clear\n")
                            sys.stderr.write("="*70 + "\n\n")
                            sys.stderr.flush()
            except Exception as e:
                console.print(f"[yellow]⚠ save_on_critical processing failed: {e}[/yellow]")

            # Output stop message
            msg = "🛑 CRITICAL: Token limit exceeded - AUTO STOP TRIGGERED\n"
            msg += f"   Current session: {current_tokens:,} tokens\n"
            if compact_triggered:
                msg += "   Context compression in progress...\n"
            msg += "   Session terminated to prevent cost overrun\n\n"
            sys.stderr.write(msg)
            sys.stderr.flush()
            sys.exit(2)  # Don't block, let additionalContext pass through

        sys.exit(0)
    except SystemExit:
        raise  # Re-raise SystemExit
    except Exception as e:
        console.print(f"[red]Token manager error: {e}[/red]", style="dim")
        sys.exit(0)  # Don't block on other errors


# ============================================================================
# Command: reset
# ============================================================================

@app.command()
def reset(
    delete_sessions: bool = typer.Option(
        False,
        "--delete-sessions",
        help="Delete session records instead of archiving"
    )
):
    """
    Reset token usage counters.

    By default, archives session records. Use --delete-sessions to remove them.
    """
    usage = load_token_usage()
    if not usage:
        console.print("[red]Failed to load token usage data[/red]")
        sys.exit(1)

    # Store pre-reset info
    old_total = usage.get('total_accumulated', 0)
    old_sessions = len(usage.get('sessions', {}))

    # Process sessions
    if not delete_sessions:
        # Archive all sessions
        for session_id in usage.get('sessions', {}):
            usage['sessions'][session_id]['status'] = 'archived'
    else:
        # Delete all sessions
        usage['sessions'] = {}

    # Reset accumulated tokens
    usage['total_accumulated'] = 0
    usage['last_reset'] = datetime.now(timezone.utc).isoformat()
    usage['reset_count'] = usage.get('reset_count', 0) + 1

    # Save
    if not save_token_usage(usage):
        sys.exit(1)

    # Success message
    console.print(Panel(
        f"[green]✓ Token usage reset complete[/green]\n\n"
        f"Before reset: {old_total:,} tokens ({old_sessions} sessions)\n"
        f"After reset: 0 tokens\n"
        f"Reset count: {usage['reset_count']}",
        title="Token Reset",
        border_style="green"
    ))

    sys.exit(0)


# ============================================================================
# Command: check-continuity
# ============================================================================

def is_continued_session() -> bool:
    """
    Check if current session is a continuation of previous session.

    Logic:
    1. Get current session file - if doesn't exist or very small → new session
    2. Check last modified time - if very recent (< 30 seconds) → likely new session
    3. Load token-usage.json to get last tracked session ID
    4. If current session ID == last session ID → continued
    5. Check first 20 lines of current session for previous session ID
    6. If previous session ID found in content → continued (claude --continue)
    7. Otherwise → new session

    Returns:
        True if session is continued, False if new session
    """
    session_file = get_session_file_path()
    if not session_file:
        return False

    # Check if session file is very new (less than 5 lines = likely new session)
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
            if line_count < 5:
                return False
    except Exception:
        return False

    # Check if file was just created (< 30 seconds ago)
    try:
        import time
        file_age = time.time() - session_file.stat().st_mtime
        if file_age < 30:  # Less than 30 seconds old = new session
            return False
    except Exception:
        pass

    usage_data = load_token_usage()
    last_session_id = usage_data.get('current_session', '')

    if not last_session_id:
        return False

    current_session_id = session_file.stem

    # Same session ID → definitely continued
    if current_session_id == last_session_id:
        return True

    # Check if previous session ID is mentioned in first 20 lines
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 20:
                    break
                if last_session_id in line:
                    return True
    except Exception:
        pass

    return False


def should_reset_token_usage() -> bool:
    """
    Determine if token-usage.json should be reset for a new session.

    Returns:
        True if should reset (new session), False otherwise
    """
    return not is_continued_session()


@app.command()
def check_continuity():
    """
    Check if session is continued from previous.

    Returns exit code 0 if continued, 1 if new session.
    """
    is_continued = is_continued_session()

    usage_data = load_token_usage()
    last_session = usage_data.get('current_session', 'N/A')

    session_file = get_session_file_path()
    current_session = session_file.stem if session_file else 'N/A'

    console.print("\n[bold cyan]Session Continuity Check[/bold cyan]\n")
    console.print(f"Last tracked session: [yellow]{last_session}[/yellow]")
    console.print(f"Current session:      [yellow]{current_session}[/yellow]")
    console.print(f"Is continued:         [{'green' if is_continued else 'red'}]{is_continued}[/]")
    console.print(f"Should reset:         [{'red' if not is_continued else 'green'}]{not is_continued}[/]\n")

    sys.exit(0 if is_continued else 1)


# ============================================================================
# Command: status
# ============================================================================

@app.command()
def status():
    """
    Display current token usage status.

    Shows current session tokens, total accumulated tokens, and thresholds.
    """
    # Get real-time token usage from session file
    latest_usage = get_latest_token_usage()

    usage_data = load_token_usage()
    limits = load_token_limits()

    current_session_id = usage_data.get('current_session', '')
    sessions = usage_data.get('sessions', {})

    if not current_session_id or current_session_id not in sessions:
        console.print("[yellow]No active session found[/yellow]")
        return

    # Use real-time token count if available, otherwise use saved value
    if latest_usage:
        current_tokens = latest_usage['total_tokens']
    else:
        session_data = sessions[current_session_id]
        current_tokens = session_data.get('tokens', 0)

    total_accumulated = usage_data.get('total_accumulated', 0) + current_tokens

    # Thresholds
    session_limits = limits.get('session_limits', {})
    total_limits = limits.get('total_limits', {})

    session_warning = session_limits.get('warning', 100000)
    session_critical = session_limits.get('critical', 130000)
    total_warning = total_limits.get('warning', 400000)
    total_critical = total_limits.get('critical', 500000)

    # Table
    table = Table(title="Token Usage Status", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")
    table.add_column("Threshold", style="yellow", justify="right")
    table.add_column("Percentage", style="magenta", justify="right")

    session_pct = f"{current_tokens*100/session_critical:.1f}%"
    total_pct = f"{total_accumulated*100/total_critical:.1f}%"

    table.add_row(
        "Current Session",
        f"{current_tokens:,}",
        f"{session_critical:,}",
        session_pct
    )
    table.add_row(
        "Total Accumulated",
        f"{total_accumulated:,}",
        f"{total_critical:,}",
        total_pct
    )
    table.add_row(
        "Reset Count",
        str(usage_data.get('reset_count', 0)),
        "-",
        "-"
    )

    console.print(table)

    # Progress bars
    console.print("\n[bold]Session Progress:[/bold]")
    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        progress.add_task("", total=session_critical, completed=current_tokens)

    console.print("\n[bold]Total Progress:[/bold]")
    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        progress.add_task("", total=total_critical, completed=total_accumulated)

    # Check and display warnings/critical messages
    session_auto_stop = session_limits.get('auto_stop', False)
    total_auto_stop = total_limits.get('auto_stop', False)

    if session_auto_stop:
        check_value = current_tokens
        check_critical = session_critical
        check_warning = session_warning
        check_type = "Session"
    else:
        check_value = total_accumulated
        check_critical = total_critical
        check_warning = total_warning
        check_type = "All"

    console.print()
    if check_value >= check_critical:
        console.print(f"[red bold]🚨 CRITICAL: {check_type} Token {check_value:,} / {check_critical:,} excess![/red bold]")
    elif check_value >= check_warning:
        percentage = check_value * 100 // check_critical
        console.print(f"[yellow]⚠️  WARNING: {check_type} Token {check_value:,} / {check_critical:,} ({percentage}%)[/yellow]")
    else:
        console.print(f"[green]✓ Normal: {check_type} Token usage remains stable[/green]")

    console.print()


@app.command()
def startup():
    """
    Display token usage on session startup if enabled.

    Called by session_start.py to show initial token status.
    """
    limits = load_token_limits()
    display = limits.get('display', {})

    if not display.get('show_on_startup', False):
        sys.exit(0)

    usage_data = load_token_usage()
    current_session_id = usage_data.get('current_session', '')
    sessions = usage_data.get('sessions', {})

    if not current_session_id or current_session_id not in sessions:
        sys.exit(0)

    session_data = sessions[current_session_id]
    current_tokens = session_data.get('tokens', 0)
    total_accumulated = usage_data.get('total_accumulated', 0)

    session_limits = limits.get('session_limits', {})
    total_limits = limits.get('total_limits', {})

    session_warning = session_limits.get('warning', 100000)
    session_critical = session_limits.get('critical', 130000)
    total_warning = total_limits.get('warning', 400000)
    total_critical = total_limits.get('critical', 500000)

    format_type = display.get('format', 'minimal')

    if format_type == 'silent':
        sys.exit(0)
    elif format_type == 'minimal':
        session_pct = current_tokens * 100 // session_critical if session_critical > 0 else 0
        total_pct = total_accumulated * 100 // total_critical if total_critical > 0 else 0
        msg = f"📊 Session: {current_tokens:,}/{session_critical:,} ({session_pct}%) | Total: {total_accumulated:,}/{total_critical:,} ({total_pct}%)\n"
        sys.stderr.write(msg)
        sys.stderr.flush()
    else:  # detailed
        console.print()
        console.print("[bold cyan]Token Usage at Startup:[/bold cyan]")
        console.print(f"  Session: {current_tokens:,} / {session_critical:,} ({current_tokens*100//session_critical}%)")
        console.print(f"  Total:   {total_accumulated:,} / {total_critical:,} ({total_accumulated*100//total_critical}%)")
        console.print()

    sys.exit(0)


if __name__ == '__main__':
    app()
