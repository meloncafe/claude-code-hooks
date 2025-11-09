#!/usr/bin/env python3
"""
Example Project Pre-Session Hook

Executed at session start to display the following:
1. Project information and current environment
2. ChromaDB context search guide
3. Work rules and instructions
4. Completion checklist
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

from common.config import load_config
from common.logger import HookLogger
from common.formatting import (
    console,
    print_rule,
    create_info_table,
    create_rules_table,
)
from rich.panel import Panel
from rich.padding import Padding
from rich.table import Table
from rich import box

from common.servers import SERVER_CONFIG, get_server_status_internal
from token_manager import is_continued_session, should_reset_token_usage


def detect_work_context() -> str:
    """
    Automatic detection of current work context (frontend/backend).
    Determined by analyzing modified files via `git status`.
    """
    try:
        project_root = Path(__file__).parent.parent.parent

        result = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(project_root)
        )

        if result.returncode != 0:
            return 'backend'

        modified_files = result.stdout.strip().split('\n')
        if not modified_files or modified_files == ['']:
            return 'backend'

        frontend_indicators = [
            'app/',  # React
            'components/',
            'pages/',
            'features/',
            '.tsx', '.jsx', '.ts', '.css', '.scss',
            'vite.config', 'tsconfig.json'
        ]

        backend_indicators = [
            'example_project/',
            '.py',
            'pyproject.toml', 'poetry.lock',
            'alembic/', 'migrations/',
            'tests/integration/', 'tests/unit/'
        ]

        frontend_count = 0
        backend_count = 0

        for line in modified_files:
            if not line.strip():
                continue
            filepath = line[3:].strip() if len(line) > 3 else ''

            if '.claude/' in filepath:
                continue

            for indicator in frontend_indicators:
                if indicator in filepath:
                    frontend_count += 1
                    break

            for indicator in backend_indicators:
                if indicator in filepath:
                    backend_count += 1
                    break

        if frontend_count > backend_count:
            return 'frontend'

        return 'backend'

    except Exception:
        return 'backend'


def detect_environment(config: Dict[str, Any]) -> tuple[str, str]:
    """Current Environment Detection (Docker/Mac/WSL)"""
    paths = config['project_paths']

    cwd = Path.cwd()

    if str(cwd).startswith(paths.get('docker', '/workspaces/')):
        return 'DOCKER', paths.get('docker', '')

    if str(cwd).startswith('/mnt/c/'):
        return 'WSL', paths.get('wsl', '')

    if str(cwd).startswith('/Users/'):
        return 'MAC', paths.get('mac', '')

    return 'UNKNOWN', str(cwd)


def print_header(config: Dict[str, Any], env: str, project_path: str, work_context: str) -> None:
    """Output session start header"""
    collection = config['primary_collection']
    messages = config['messages']

    # Current Date and Time
    now = datetime.now(tz=ZoneInfo('UTC'))
    current_date = now.strftime("%Y-%m-%d (%A)")
    current_time = now.strftime("%H:%M:%S")

    console.print()
    print_rule(messages['session_start'], style="bold magenta")

    info_data = {
        messages['date_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): current_date,
        messages['time_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): current_time,
        messages['environment_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): env,
        messages['project_path_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): project_path,
        messages['work_context_prefix'].replace('🎯 ', ''): work_context.upper(),
    }
    table = create_info_table(info_data)
    console.print(table)

    console.print()
    server_table = Table(
        title="SERVER STATUS",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED
    )
    server_table.add_column("Category", style="cyan")
    server_table.add_column("Type", style="magenta")
    server_table.add_column("Port", justify="right")
    server_table.add_column("Status", justify="center")
    server_table.add_column("PID", justify="right")

    # Backend servers
    for backend_type, config in SERVER_CONFIG["backend"].items():
        is_running, _, pid = get_server_status_internal("backend", backend_type)
        status = "[green]RUNNING[/]" if is_running else "[yellow]STOPPED[/]"
        pid_str = str(pid) if pid else "-"
        server_table.add_row("Backend", backend_type, str(config["port"]), status, pid_str)

    # Frontend servers
    for frontend_type, config in SERVER_CONFIG["frontend"].items():
        is_running, _, pid = get_server_status_internal("frontend", frontend_type)
        status = "[green]RUNNING[/]" if is_running else "[yellow]STOPPED[/]"
        pid_str = str(pid) if pid else "-"
        server_table.add_row("Frontend", frontend_type, str(config["port"]), status, pid_str)

    console.print(server_table)

    print_rule("", style="dim")
    console.print(f"[bold cyan]{messages['chromadb_collection_prefix']}[/bold cyan] [green]{collection}[/green]")
    console.print()


def print_mcp_priority(config: Dict[str, Any]) -> None:
    """MCP Tool Priority Output"""
    priority = config.get('mcp_tools_priority', [])

    if not priority:
        return

    console.print("\n[bold cyan]MCP Tool Priority:[/bold cyan]")
    for i, tool in enumerate(priority, 1):
        console.print(f"   [green]{i}.[/green] [white]{tool}[/white]")
    console.print()


def print_context_search_guide(config: Dict[str, Any]) -> None:
    """
    ChromaDB Context Auto-Retrieval Guide.
    Trigger remote server search via MCP tool.
    """
    context_search = config['context_search']
    messages = config['messages']
    display = config['display']

    if not context_search['enabled'] or not display.get('show_context_search', True):
        return

    collection = context_search['collection']
    queries = context_search['search_queries']
    n_results = context_search['n_results']

    console.print(f"{messages['context_search_guide']}")
    console.print(f"   {messages['collection_label']} {collection}")
    console.print(f"   {messages['results_label']} {n_results}")
    console.print()

    console.print("   [yellow]WARNING:[/yellow] Perform the following search immediately (required):")
    console.print()

    if queries:
        first_query = queries[0]
        console.print(f"""   chromadb:chroma_query_documents(
       collection_name="{collection}",
       query_texts=["{first_query}"],
       n_results={n_results}
   )""")
        console.print()

    if len(queries) > 1:
        console.print(f"   {messages['recommended_queries']}")
        for query in queries[1:]:
            console.print(f"   - {query}")
        console.print()


def get_project_specific_rules(config: Dict[str, Any]) -> list[str]:
    """
    Return specialized rules by project type.
    Supports both backend and frontend in monorepo environments.
    """
    project_type = config.get('project_type', '')
    rules = []

    if project_type == 'python_fastapi':
        rules.extend([
            "FastAPI dependency injection Make full use of",
            "Pydantic schema validation is essential (schemas package)",
            "Compliance with the Repository/Service Pattern",
            "mypy strict mode must pass",
            "Alembic Migration Synchronization Verification",
        ])

    return rules


def print_guidelines(config: Dict[str, Any]) -> None:
    """
    Output work instructions.
    Dynamically display response language, default prompts, Sentry settings, etc.
    """
    guidelines = config.get('guidelines', [])
    messages = config['messages']
    display = config['display']
    response_language = config.get('response_language', 'English')
    default_prompt = config.get('default_prompt', '')

    settings = load_config('settings.json')
    sentry_config = settings.get('sentry', {})

    if not display.get('show_task_instructions', True):
        return

    dynamic_guidelines = []

    dynamic_guidelines.append(f"[LANGUAGE]: {response_language}")

    if default_prompt:
        dynamic_guidelines.append(f"[DEFAULT_PROMPT]: {default_prompt}")

    if sentry_config.get('enabled'):
        org = sentry_config.get('organization', '')
        projects = sentry_config.get('projects', [])
        if org:
            sentry_info = f"[SENTRY]: Organization={org}"
            if projects:
                sentry_info += f", Projects={', '.join(projects)}"
            dynamic_guidelines.append(sentry_info)

    if guidelines:
        dynamic_guidelines.extend(guidelines)

    project_rules = get_project_specific_rules(config)
    if project_rules:
        dynamic_guidelines.append("")
        dynamic_guidelines.append("[PROJECT]:")
        dynamic_guidelines.extend(project_rules)

    console.print(f"{messages['task_instructions']}")
    for guideline in dynamic_guidelines:
        if guideline:
            console.print(f"   {guideline}")
        else:
            console.print()
    console.print()


def print_work_rules(config: Dict[str, Any]) -> None:
    """Output Work Rules"""
    work_rules = config['work_rules']
    messages = config['messages']

    if not work_rules:
        return

    console.print(f"\n[bold cyan]{messages['work_rules']}[/bold cyan]")
    table = create_rules_table(work_rules)
    console.print(table)
    console.print()


def print_completion_checklist(config: Dict[str, Any]) -> None:
    """Print Completion Checklist"""
    checklist = config['completion_checklist']
    messages = config['messages']

    if not checklist:
        return

    console.print(f"\n[bold green]{messages['completion_checklist']}[/bold green]")
    for item in checklist:
        console.print(f"   [green]{item}[/green]")
    console.print()


def print_code_style_rules(config: Dict[str, Any]) -> None:
    """Code Style Rules Output (Using All Settings)"""
    code_style_rules = config.get('code_style_rules', {})
    messages = config['messages']

    if not code_style_rules:
        return

    console.print(f"{messages['code_style']}")

    comments = code_style_rules.get('comments', {})
    if comments:
        console.print("   Note:")
        style = comments.get('style', '')
        if style:
            console.print(f"      • Style: {style}")
        language = comments.get('language', '')
        if language:
            console.print(f"      • Language: {language}")

        forbidden_phrases = comments.get('forbidden_phrases', [])
        if forbidden_phrases:
            console.print(f"      • Forbidden phrases: {', '.join(f'{p!r}' for p in forbidden_phrases)}")

        forbidden_names = comments.get('forbidden_names', [])
        if forbidden_names:
            console.print(f"      • Forbidden names: {', '.join(forbidden_names)}")

        no_redundant = comments.get('no_redundant_comments', '')
        if no_redundant:
            console.print(f"      • {no_redundant}")

    architecture = code_style_rules.get('architecture', {})
    if architecture:
        console.print("   Architecture:")
        for key, value in architecture.items():
            if isinstance(value, list):
                value_str = ', '.join(str(v) for v in value)
            else:
                value_str = str(value)
            key_display = key.replace('_', ' ').title()
            console.print(f"      • {key_display}: {value_str}")

    console.print()


def print_footer(config: Dict[str, Any]) -> None:
    """Session Start Footer Output"""
    messages = config['messages']

    critical_checklist = config.get('critical_checklist', {})

    if not critical_checklist:
        return

    print_rule("", style="dim")
    console.print(f"\n[bold cyan]{messages['start_reminder']}[/bold cyan]\n")

    # 중요 가이드라인 강조 패널
    warning_content = "[bold]Important: Verify the mandatory guidelines that must be followed.[/bold]"
    console.print(
        Panel(
            warning_content,
            style="bold yellow",
            border_style="yellow",
            padding=(0, 2),
        )
    )
    console.print()

    section_config = [
        ("required", "Required Items", "red"),
        ("tools", "Tool Usage", "cyan"),
        ("validation", "Verification", "magenta"),
        ("important", "Important", "yellow")
    ]

    for section_key, section_title, section_color in section_config:
        items = critical_checklist.get(section_key, [])
        if items:
            console.print(f"   [bold {section_color}][{section_title}][/bold {section_color}]")
            for item in items:
                console.print(f"      • {item}")
            console.print()

    confirmation_text = """[bold green]If you have thoroughly reviewed the above guidelines, the following message will be displayed.:[/bold green]

   [cyan]'{{Date}}-{{Time}} : Context verification complete'[/cyan]

[bold red]Do not start the task until this message is displayed.[/bold red]"""

    console.print(
        Panel(
            confirmation_text,
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()

    console.print(f"[bold green]{messages.get('session_ready', '')}[/bold green]")
    print_rule("", style="bold magenta")
    console.print()


def get_current_token_usage() -> Optional[int]:
    """
    Get current token usage from environment or file.

    Claude Code provides token usage through:
    - Environment variable: CLAUDE_TOKEN_USAGE
    - Temporary file: /tmp/claude-token-usage.txt

    Returns:
        Current token count or None if not available
    """
    # Try environment variable first
    token_env = os.environ.get('CLAUDE_TOKEN_USAGE')
    if token_env:
        try:
            return int(token_env)
        except ValueError:
            pass

    # Try temporary file
    token_file = Path('/tmp/claude-token-usage.txt')
    if token_file.exists():
        try:
            content = token_file.read_text().strip()
            return int(content)
        except (ValueError, OSError):
            pass

    return None


def print_token_status(config: Dict[str, Any]) -> None:
    """
    Token Usage Status Display (JSON-based).

    - Current session tokens
    - Total accumulated tokens
    - Warning and reset guide
    """
    import json

    # token-usage.json 로드
    usage_path = Path.home() / '.claude' / 'sessions' / 'token-usage.json'
    if not usage_path.exists():
        return

    try:
        with open(usage_path, 'r') as f:
            usage_data = json.load(f)
    except Exception:
        return

    try:
        limits_config = load_config('token-limits.json')
    except FileNotFoundError:
        limits_config = {
            "session_limits": {"warning": 150000, "critical": 180000},
            "total_limits": {"warning": 400000, "critical": 500000}
        }

    if not limits_config.get('enabled', True):
        return

    current_session_id = usage_data.get('current_session', '')
    sessions = usage_data.get('sessions', {})

    if current_session_id not in sessions:
        return

    session_data = sessions[current_session_id]
    current_tokens = session_data.get('tokens', 0)
    total_accumulated = usage_data.get('total_accumulated', 0) + current_tokens

    session_limits = limits_config.get('session_limits', {})
    total_limits = limits_config.get('total_limits', {})
    display = limits_config.get('display', {})

    session_warning = session_limits.get('warning', 150000)
    session_critical = session_limits.get('critical', 180000)
    total_warning = total_limits.get('warning', 400000)
    total_critical = total_limits.get('critical', 500000)

    show_warning = False
    is_critical = False

    if current_tokens >= session_critical or total_accumulated >= total_critical:
        is_critical = True
        show_warning = display.get('show_on_critical', True)
    elif current_tokens >= session_warning or total_accumulated >= total_warning:
        show_warning = display.get('show_on_warning', True)

    if not show_warning:
        return

    from rich.progress import Progress, BarColumn, TextColumn
    from rich.panel import Panel

    style = "red bold" if is_critical else "yellow"
    title = "🚨 Token Usage Warning" if is_critical else "⚠️  Token Usage Notification"

    print_rule(title, style=style)
    console.print()

    session_pct = min(100, int(current_tokens * 100 / session_critical))
    session_color = "red" if current_tokens >= session_critical else "yellow" if current_tokens >= session_warning else "green"

    console.print(f"  [bold]Current session:[/bold] {current_tokens:,} / {session_critical:,} tokens ({session_pct}%)")

    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=40, complete_style=session_color),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("", total=session_critical, completed=current_tokens)

    console.print()

    total_pct = min(100, int(total_accumulated * 100 / total_critical))
    total_color = "red" if total_accumulated >= total_critical else "yellow" if total_accumulated >= total_warning else "green"

    console.print(f"  [bold]Total Cumulative:[/bold] {total_accumulated:,} / {total_critical:,} tokens ({total_pct}%)")

    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=40, complete_style=total_color),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("", total=total_critical, completed=total_accumulated)

    console.print()

    # 리셋 가이드
    if is_critical or total_accumulated >= total_warning:
        console.print(Panel(
            "[yellow]💡 To reset the token,:[/yellow]\n"
            "  • Natural language: [cyan]\"Please reset the token.\"[/cyan] or [cyan]\"Token Initialization\"[/cyan]\n"
            "  • CLI: [cyan]python3 .claude/hook_scripts/reset_tokens.py[/cyan]",
            border_style="yellow",
            padding=(0, 1)
        ))
        console.print()

    print_rule("", style="dim")


def check_context_recovery_needed() -> Dict[str, Any]:
    """
    Check if context recovery is needed and available.
    Returns dictionary with recovery options.
    """
    project_root = Path(__file__).parent.parent.parent
    recovery_dir = project_root / ".claude" / "recovery"
    backup_dir = project_root / ".claude" / "backups"

    recovery_options: Dict[str, Any] = {
        "has_recovery": False,
        "compressed_file": None,
        "latest_backup": None,
        "backup_files": []
    }

    compact_recovery_exists = False

    # 1. Check for compressed context data
    if recovery_dir.exists():
        compact_recovery = recovery_dir / "compact-recovery.json"
        if compact_recovery.exists():
            compact_recovery_exists = True
            # Check if recovery has already been completed
            try:
                import json
                with open(compact_recovery, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # Only show guidance if NOT already recovered
                if not state.get('recovered', False):
                    recovery_options["has_recovery"] = True
                    recovery_options["compressed_file"] = str(compact_recovery)
            except Exception:
                # If can't read file, assume recovery needed
                recovery_options["has_recovery"] = True
                recovery_options["compressed_file"] = str(compact_recovery)

    # 2. Check for backup files ONLY if compact-recovery.json does NOT exist
    if not compact_recovery_exists and backup_dir.exists():
        # Find all conversation backup files
        backup_files = sorted(
            backup_dir.glob("conversation_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Most recent first
        )

        if backup_files:
            recovery_options["has_recovery"] = True
            recovery_options["latest_backup"] = str(backup_files[0])
            recovery_options["backup_files"] = [str(f) for f in backup_files[:5]]  # Top 5 most recent

    return recovery_options


def print_context_recovery_guidance(recovery_options: Dict[str, Any]):
    """
    Display context recovery guidance panel for Claude.
    """
    if not recovery_options["has_recovery"]:
        return  # No recovery options available, skip

    print_rule("Step 1: Context Recovery Verification", style="bold cyan")
    console.print()

    # Priority message for Claude
    priority_msg = """[bold yellow]
================================================================================
IMPORTANT: The summary below is the official context for this session.
Prioritize the content below over Claude's auto-generated summaries.
================================================================================
[/bold yellow]"""

    console.print(priority_msg)
    console.print()

    # Build recovery guidance content
    guidance_lines = []

    if recovery_options["compressed_file"]:
        guidance_lines.append(
            f"✓ [green]Compressed context file found:[/green] {recovery_options['compressed_file']}"
        )
        guidance_lines.append(
            "  → [cyan]`.claude/hooks.py context-recovery` Can be automatically restored using a command[/cyan]"
        )
        guidance_lines.append("")

    # Check for compact-recovery.json (saved context from critical token state)
    compact_recovery = Path(".claude/recovery/compact-recovery.json")
    if compact_recovery.exists():
        try:
            import json
            with open(compact_recovery, 'r') as f:
                recovery_data = json.load(f)

            timestamp = recovery_data.get('timestamp', '')
            summary_length = recovery_data.get('summary_length', 0)

            if timestamp and summary_length > 0:
                from datetime import datetime
                saved_time = datetime.fromisoformat(timestamp)
                time_diff = datetime.now() - saved_time
                hours_ago = int(time_diff.total_seconds() / 3600)

                guidance_lines.append(
                    f"📌 [green]Saved Work Context Found:[/green] Saved {hours_ago} hours ago"
                )
                guidance_lines.append(
                    "  → [cyan]Requesting 'Continue previous task' or 'Review last task' triggers context recovery.[/cyan]"
                )
                guidance_lines.append("")
        except Exception:
            pass

    if recovery_options["latest_backup"]:
        guidance_lines.append(
            f"✓ [green]Latest backup file found:[/green] {Path(recovery_options['latest_backup']).name}"
        )
        guidance_lines.append(
            f"  → [cyan]Path: {recovery_options['latest_backup']}[/cyan]"
        )

        if len(recovery_options["backup_files"]) > 1:
            guidance_lines.append(
                f"  → [dim]Additional {len(recovery_options['backup_files'])-1} backups available[/dim]"
            )
        guidance_lines.append("")

    # Instructions for Claude
    guidance_lines.append("[bold cyan]Claude's Instructions:[/bold cyan]")
    guidance_lines.append("")
    guidance_lines.append(
        "1. [yellow]When the user requests to restore the previous context,:[/yellow]"
    )
    guidance_lines.append(
        "   - If there is compressed data `.claude/hooks.py context-recovery` Execute"
    )
    guidance_lines.append(
        "   - If there is no compressed data, read the latest backup file and summarize."
    )
    guidance_lines.append("")
    guidance_lines.append(
        "2. [yellow]Backup File Convention:[/yellow]"
    )
    guidance_lines.append(
        "   - Summarize the contents of the 'messages' array in the JSON file in chronological order."
    )
    guidance_lines.append(
        "   - Organized around the purpose of the work, key changes, major decisions, and unfinished tasks"
    )
    guidance_lines.append("")
    guidance_lines.append(
        "3. [yellow]Recovery Priority:[/yellow] Compressed file → Last backup → User selection"
    )

    guidance_content = "\n".join(guidance_lines)

    # Display guidance panel
    console.print(
        Panel(
            guidance_content,
            title="[bold green]Context Recovery Guide[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


def main():
    """Main Function"""
    logger = HookLogger("pre-session-hook") if HookLogger else None

    try:
        if logger:
            logger.log_start()

        # ========================================
        # Step 0: Session Continuity Check and Token Initialization
        # ========================================
        if should_reset_token_usage():
            import json
            from datetime import datetime, UTC

            usage_path = Path.home() / '.claude' / 'sessions' / 'token-usage.json'
            usage_path.parent.mkdir(parents=True, exist_ok=True)

            new_data = {
                "current_session": "",
                "sessions": {},
                "total_accumulated": 0,
                "last_reset": datetime.now(UTC).isoformat(),
                "reset_count": 0
            }

            with open(usage_path, 'w') as f:
                json.dump(new_data, f, indent=2)

            if logger:
                logger.log_info("New session detected - token-usage.json initialization complete")

        config = load_config('pre-session.json')

        if logger:
            logger.log_info(
                "Settings loaded",
                project_name=config.get('project_name', 'unknown'),
                primary_collection=config.get('primary_collection', 'example_project_context')
            )

        env, project_path = detect_environment(config)

        work_context = detect_work_context()

        if logger:
            logger.log_info(
                "Environmental and operational context detection complete",
                environment=env,
                project_path=project_path,
                work_context=work_context
            )

        # ========================================
        # Step 1: Context Recovery Verification
        # ========================================
        recovery_options = check_context_recovery_needed()
        if recovery_options["has_recovery"]:
            print_context_recovery_guidance(recovery_options)

            if logger:
                logger.log_info(
                    "Context Recovery Guide Display Complete",
                    has_compressed=recovery_options["compressed_file"] is not None,
                    has_backup=recovery_options["latest_backup"] is not None,
                    backup_count=len(recovery_options["backup_files"])
                )

        # ========================================
        # Step 2: Project Information and Work Guide
        # ========================================
        if recovery_options["has_recovery"]:
            print_rule("Step 2: Project Information and Work Guide", style="bold cyan")
            console.print()

        print_token_status(config)

        print_header(config, env, project_path, work_context)
        print_mcp_priority(config)
        print_context_search_guide(config)
        print_guidelines(config)
        print_work_rules(config)
        print_code_style_rules(config)
        print_completion_checklist(config)
        print_footer(config)

        if logger:
            logger.log_end(
                success=True,
                sections_printed=[
                    "context_recovery" if recovery_options["has_recovery"] else None,
                    "token_status" if get_current_token_usage() else None,
                    "header",
                    "mcp_priority" if config.get('mcp_tools_priority') else None,
                    "context_search" if config['context_search']['enabled'] else None,
                    "guidelines" if config.get('guidelines') else None,
                    "project_rules" if get_project_specific_rules(config) else None,
                    "work_rules" if config.get('work_rules') else None,
                    "code_style_rules" if config.get('code_style_rules') else None,
                    "checklist" if config.get('completion_checklist') else None,
                ]
            )

        sys.exit(0)

    except Exception as e:
        error_msg = f"Error occurred: {e}"
        console.print(f"[red]ERROR:[/red] {error_msg}")
        import traceback
        traceback.print_exc()

        if logger:
            logger.log_end(success=False, error=str(e))

        sys.exit(1)


if __name__ == "__main__":
    main()
