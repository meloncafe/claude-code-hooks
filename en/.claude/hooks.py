#!/usr/bin/env python3
"""
Example Project Hook Scripts CLI Manager
"""
import sys
from pathlib import Path

HOOK_SCRIPTS_DIR = Path(__file__).parent / "hook_scripts"
sys.path.insert(0, str(HOOK_SCRIPTS_DIR))

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="hooks",
    help="Example Project Hook Scripts CLI",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def session_start(
    skip_recovery: bool = typer.Option(
        False,
        "--skip-recovery",
        help="Skip the context recovery step"
    ),
    skip_guide: bool = typer.Option(
        False,
        "--skip-guide",
        help="Skip Project Guide Display"
    )
):
    """
    Session Start - Context Recovery and Project Guide Display

    Automatically Run:
    1. Context Recovery Helper
    2. Pre-Session Hook (Project Information and Guide)
    """
    from hook_scripts.session_start import main as session_start_main

    console.print("[cyan]세션 시작 중...[/cyan]")
    try:
        session_start_main()
    except SystemExit:
        pass


@app.command()
def context_recovery():
    """
    Execute Context Recovery

    Automatically recover compressed contexts:
    - Load saved summaries from recovery status files
    - Automatically load recent backup files
    - Automatically provide context to new sessions
    """
    from hook_scripts.context_recovery_helper import main as recovery_main

    console.print("[cyan]Recovering context...[/cyan]")
    try:
        recovery_main()
    except SystemExit:
        pass


@app.command()
def pre_session():
    """
    Display project information and task guide

    Display at session start:
    - Project information and current environment
    - ChromaDB context search guide
    - Task rules and instructions
    - Completion checklist
    """
    from hook_scripts.pre_session_hook import main as pre_session_main

    console.print("[cyan]Project Guide Display...[/cyan]")
    try:
        pre_session_main()
    except SystemExit:
        pass


@app.command()
def auto_compact(
    threshold: float = typer.Option(
        None,
        "--threshold",
        help="Compression threshold (0.0-1.0)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force Compression Execution"
    )
):
    """
    Automatic Context Compression

    When context exceeds the threshold, it automatically:
    - Creates a backup
    - Generates an AI summary
    - Saves to ChromaDB
    - Creates a recovery file
    """
    console.print("[cyan]Checking context compression...[/cyan]")
    console.print("[yellow]Note: Must be executed using the PreCompact hook to function properly.[/yellow]")


@app.command()
def post_session():
    """
    Cleanup after session termination

    Execute upon session termination:
    - Clean up temporary files
    - Clean up logs
    - Save state
    """
    from hook_scripts.post_session_hook import main as post_session_main

    console.print("[cyan]Processing session termination...[/cyan]")
    try:
        post_session_main()
    except SystemExit:
        pass


@app.command()
def validate_commit(
    message: str = typer.Argument(
        None,
        help="Commit message to verify (read from stdin if not provided)"
    )
):
    """
    Git Commit Message Validation

    Validation Items:
    - Conventional Commits Format
    - Message Length
    - Prohibited Pattern Check
    - Co-authored Rules
    """
    from hook_scripts.validate_git_commit import main as validate_main

    if message:
        import io
        sys.stdin = io.StringIO(message)

    console.print("[cyan]Verifying commit message...[/cyan]")
    try:
        validate_main()
    except SystemExit as e:
        if e.code != 0:
            console.print("[red]Verification failed[/red]")
        else:
            console.print("[green]Verification passed[/green]")


@app.command()
def scan_secrets(
    path: str = typer.Argument(".", help="Scan path"),
    staged_only: bool = typer.Option(False, "--staged", help="sScan only tagged files")
):
    """
    Secret and Sensitive Information Scan

    Scan Items:
    - API Key Patterns
    - Password Patterns
    - Token Patterns
    - Sensitive File Names
    """
    import subprocess
    import json

    console.print(f"[cyan]Secret scan in progress: {path}[/cyan]")

    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": path}
    }

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPTS_DIR / "secret_scanner.py")],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr, style="dim")

        if result.returncode != 0:
            console.print(f"[yellow]Warning: An error occurred during scanning. (exit code: {result.returncode})[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def check_mocks(
    path: str = typer.Argument(".", help="Path to inspect")
):
    """
    Mock Code and Placeholder Check

    Check Items:
    - TODO comments
    - Mock data
    - Placeholder code
    - Unimplemented functions
    """
    import subprocess
    import json

    console.print(f"[cyan]Checking mock code: {path}[/cyan]")

    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": path}
    }

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPTS_DIR / "no_mock_code.py")],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr, style="dim")

        if result.returncode != 0:
            console.print(f"[yellow]Warning: Error occurred during check (exit code: {result.returncode})[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def validate_timestamp():
    """
    Verifying timestamps within code

    Verification items:
    - Hardcoded dates
    - Outdated timestamps
    - Expired time values
    """
    import subprocess
    import json

    console.print("[cyan]Timestamp verification in progress...[/cyan]")

    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {}
    }

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPTS_DIR / "timestamp_validator.py")],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr, style="dim")

        if result.returncode != 0:
            console.print(f"[yellow]Warning: An error occurred during verification. (exit code: {result.returncode})[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def view_logs(
    script: str = typer.Argument(None, help="Script name (e.g., session_start)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of logs to query"),
    errors: bool = typer.Option(False, "--errors", "-e", help="Only display errors"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """Hook Log Inquiry"""
    import subprocess

    cmd = [sys.executable, str(HOOK_SCRIPTS_DIR / "view_logs.py"), "view"]
    if script:
        cmd.append(script)
    cmd.extend(["--limit", str(limit)])
    if errors:
        cmd.append("--errors")
    if json_output:
        cmd.append("--json")

    subprocess.run(cmd)


@app.command()
def server(
    action: str = typer.Argument(..., help="Server Action: list, status, start-backend, start-frontend, stop, stop-all"),
    category: str = typer.Argument(None, help="Server category (backend/frontend) or type"),
    server_type: str = typer.Argument(None, help="Server Type (main/auth/example)")
):
    """
    Development Server Management

    Actions:
    - list: Check all server statuses
    - status <category> <type>: Check server status
    - start-backend [type]: Start backend server (default: auth-example)
    - start-frontend [type]: Start frontend server (default: auth-example)
    - stop <category> <type>: Stop server
    - stop-all: Stop all running servers

    Example:
        .claude/hooks server list
        .claude/hooks server status backend auth-example
        .claude/hooks server start-backend auth-example
        .claude/hooks server start-backend main
        .claude/hooks server start-frontend
        .claude/hooks server stop backend auth-example
        .claude/hooks server stop-all
    """
    import subprocess

    cmd = [sys.executable, str(HOOK_SCRIPTS_DIR / "common" / "servers.py"), action]

    if action in ["start-backend", "start-frontend"]:
        if category:
            cmd.append(category)

    elif action in ["status", "stop"]:
        if not category or not server_type:
            console.print(f"[red]Error: {action} requires the format <category> <type>[/red]")
            console.print(f"[yellow]Example: .claude/hooks server {action} backend auth-example[/yellow]")
            raise typer.Exit(1)
        cmd.append(category)
        cmd.append(server_type)

    subprocess.run(cmd)


@app.command()
def list_hooks():
    """
    Display a list of all available hook scripts
    """
    table = Table(title="Hook Scripts", show_header=True, header_style="bold cyan")
    table.add_column("Command", style="green")
    table.add_column("Description", style="white")
    table.add_column("Type", style="yellow")

    hooks = [
        ("session-start", "Session Start (Recovery + Guide)", "Lifecycle"),
        ("context-recovery", "Context Recovery", "Lifecycle"),
        ("pre-session", "Project Guide Display", "Lifecycle"),
        ("auto-compact", "Automatic Context Compression", "Lifecycle"),
        ("post-session", "Session End Cleanup", "Lifecycle"),
        ("validate-commit", "Commit Message Verification", "Git"),
        ("scan-secrets", "Secret Scan", "Security"),
        ("check-mocks", "Mock Code Check", "Quality"),
        ("validate-timestamp", "Timestamp Verification", "Quality"),
        ("view-logs", "Hook Log Inquiry", "Utility"),
        ("server", "Development Server Management", "Dev"),
        ("token-status", "Token Usage Status", "Token"),
        ("token-reset", "Token Counter Reset", "Token"),
        ("token-extract", "Token extraction (PostToolUse Hook)", "Token"),
        ("token-check", "Session Continuity Check", "Token"),
    ]

    for cmd, desc, type_ in hooks:
        table.add_row(cmd, desc, type_)

    console.print(table)
    console.print("\n[dim]Detailed information: .claude/hooks [command] --help[/dim]")


@app.command()
def token_status():
    """
    Display current token usage status

    Shows:
    - Current session tokens
    - Total accumulated tokens
    - Progress bars and thresholds
    """
    from hook_scripts.token_manager import status as token_status_cmd

    try:
        token_status_cmd()
    except SystemExit:
        pass


@app.command()
def token_reset(
    delete_sessions: bool = typer.Option(
        False,
        "--delete-sessions",
        help="Delete session records instead of archiving them"
    )
):
    """
    Token Usage Counter Reset

    By default, session records are archived,
    and can be permanently deleted using the --delete-sessions flag.
    """
    from hook_scripts.token_manager import reset as token_reset_cmd

    try:
        token_reset_cmd(delete_sessions=delete_sessions)
    except SystemExit:
        pass


@app.command()
def token_extract():
    """
    PostToolUse Hook - Token Extraction and Update

    Automatically called to extract and update token usage from the session file
    """
    from hook_scripts.token_manager import extract as token_extract_cmd

    try:
        token_extract_cmd()
    except SystemExit:
        pass


@app.command()
def token_check():
    """
    Session Continuity Check

    Verify if the current session is a continuation of the previous session
    (Distinguish between claude and claude --continue)
    """
    from hook_scripts.token_manager import check_continuity as token_check_cmd

    try:
        token_check_cmd()
    except SystemExit:
        pass


@app.callback()
def main():
    """
    Example Project Hook Scripts CLI Manager

    A CLI tool for managing all hook scripts.
    Use the --help option to view detailed usage for each command.

    Example:
        .claude/hooks session-start
        .claude/hooks validate-commit "feat: new feature"
        .claude/hooks view-logs --follow
        .claude/hooks server start --service backend
    """
    pass


if __name__ == "__main__":
    app()
