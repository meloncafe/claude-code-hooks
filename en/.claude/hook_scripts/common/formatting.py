"""
Rich Output Utility

Common Rich components and style definitions for use in hook scripts
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.theme import Theme
from rich.syntax import Syntax
from typing import List, Dict, Any, Optional, Tuple


# Defining Custom Themes
custom_theme = Theme({
    "critical": "bold red",
    "warning": "bold yellow",
    "success": "bold green",
    "info": "cyan",
    "muted": "dim",
    "header": "bold magenta",
})

# Common Console Instance (width=140 to prevent long text line breaks)
console = Console(theme=custom_theme, force_terminal=False, width=140)


def print_rule(title: str, style: str = "bold magenta") -> None:
    """Divider Output"""
    console.print(Rule(title, style=style))


def print_section_header(title: str) -> None:
    """Section Header Output"""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")


def print_critical_panel(message: str, title: str = "") -> None:
    """Critical Panel Output"""
    console.print(
        Panel(
            message,
            title=title if title else None,
            style="bold red",
            border_style="red",
        )
    )


def print_warning_panel(message: str, title: str = "") -> None:
    """Warning Panel Output"""
    console.print(
        Panel(
            message,
            title=title if title else None,
            style="bold yellow",
            border_style="yellow",
        )
    )


def print_info_panel(message: str, title: str = "") -> None:
    """Info Panel Output"""
    console.print(
        Panel(
            message,
            title=title if title else None,
            style="cyan",
            border_style="cyan",
        )
    )


def print_success_panel(message: str, title: str = "") -> None:
    """Success Panel Output"""
    console.print(
        Panel(
            message,
            title=title if title else None,
            style="bold green",
            border_style="green",
        )
    )


def print_checklist(items: List[str], title: str = "", style: str = "cyan") -> None:
    """Print Checklist"""
    if title:
        console.print(f"\n[bold {style}]{title}[/bold {style}]")
    for item in items:
        console.print(f"   {item}")


def create_info_table(data: Dict[str, Any], title: str = "") -> Table:
    """Create Information Table"""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Item", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in data.items():
        if isinstance(value, list):
            value_str = "\n".join(str(v) for v in value)
        elif isinstance(value, bool):
            value_str = "Yes" if value else "No"
        else:
            value_str = str(value)

        table.add_row(key, value_str)

    return table


def create_rules_table(rules: Dict[str, Any], title: str = "") -> Table:
    """Creating a Rule Table"""
    table = Table(title=title, show_header=False, box=None, padding=(0, 2))
    table.add_column("Item", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in rules.items():
        key_display = key.replace('_', ' ').title()

        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        elif isinstance(value, bool):
            value_str = "Yes" if value else "No"
        else:
            value_str = str(value)

        table.add_row(f"• {key_display}:", value_str)

    return table


def print_message(message: str, style: str = "white") -> None:
    """Styled message output"""
    console.print(message, style=style)


def print_git_status(
    has_changes: bool,
    staged: List[str],
    modified: List[str],
    untracked: List[str],
    messages: Dict[str, str]
) -> None:
    """Output Git status in rich format"""
    if not has_changes:
        console.print(f"\n[bold green]✓[/bold green] {messages.get('all_committed', 'All changes committed')}")
        return

    console.print(f"\n[bold yellow]Git Status:[/bold yellow] {messages.get('uncommitted_changes', 'Uncommitted changes')}\n")

    if staged:
        console.print(f"[cyan]Staged ({len(staged)}):[/cyan]")
        for file in staged[:5]:
            console.print(f"   [green]•[/green] {file}")
        if len(staged) > 5:
            console.print(f"   [dim]... and {len(staged) - 5} more[/dim]")
        console.print()

    if modified:
        console.print(f"[yellow]Modified ({len(modified)}):[/yellow]")
        for file in modified[:5]:
            console.print(f"   [yellow]•[/yellow] {file}")
        if len(modified) > 5:
            console.print(f"   [dim]... and {len(modified) - 5} more[/dim]")
        console.print()

    if untracked:
        console.print(f"[red]Untracked ({len(untracked)}):[/red]")
        for file in untracked[:5]:
            console.print(f"   [red]•[/red] {file}")
        if len(untracked) > 5:
            console.print(f"   [dim]... and {len(untracked) - 5} more[/dim]")
        console.print()


def print_metadata_template(metadata: Dict[str, Any], title: str = "Metadata Template") -> None:
    """Output metadata template in JSON format"""
    json_str = json.dumps(metadata, indent=2, ensure_ascii=False)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)

    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(syntax)
    console.print()


def print_code_example(
    code: str,
    language: str = "python",
    title: Optional[str] = None
) -> None:
    """Output code examples with syntax highlighting"""
    syntax = Syntax(code, language, theme="monokai", line_numbers=False)

    if title:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")

    console.print(syntax)
    console.print()


def create_completion_table(checks: List[Dict[str, Any]]) -> Table:
    """Create Completion Checklist Table"""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Status", style="bold", no_wrap=True, width=3)
    table.add_column("Description", style="white")

    for check in checks:
        critical = check.get('critical', False)
        description = check.get('description', '')

        marker = "[red]●[/red]" if critical else "[white]○[/white]"
        table.add_row(marker, description)

    return table


def print_key_value_list(
    items: List[Tuple[str, str]],
    title: Optional[str] = None,
    key_style: str = "cyan",
    value_style: str = "white"
) -> None:
    """Output the key-value list"""
    if title:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")

    for key, value in items:
        console.print(f"   [{key_style}]{key}:[/{key_style}] [{value_style}]{value}[/{value_style}]")

    console.print()
