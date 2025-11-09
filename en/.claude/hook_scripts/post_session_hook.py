#!/usr/bin/env python3
"""
Example Project Post-Session Hook

Executed at session end to display the following:
1. Git status check (uncommitted changes)
2. ChromaDB save notification and example
3. Completion checklist
4. Metadata template
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, List, Tuple

from common.config import load_config
from common.formatting import (
    console,
    print_rule,
    print_git_status,
    print_metadata_template,
    print_code_example,
    create_completion_table,
    print_key_value_list,
)


def check_git_status() -> Tuple[bool, List[str], List[str], List[str]]:
    """Check Git Status"""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            check=True,
            capture_output=True,
            text=True
        )

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )

        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

        modified = []
        untracked = []
        staged = []

        for line in lines:
            if not line:
                continue

            status = line[:2]
            filename = line[3:].strip()

            if status[0] in ['M', 'A', 'D', 'R', 'C']:
                staged.append(filename)
            if status[1] in ['M', 'D']:
                modified.append(filename)
            if status == '??':
                untracked.append(filename)

        has_changes = bool(modified or untracked or staged)
        return has_changes, staged, modified, untracked

    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, [], [], []


def print_header(config: Dict[str, Any]) -> None:
    """Output session termination header"""
    project_name = config.get('project_name', 'unknown')
    messages = config['messages']

    console.print()
    print_rule(f"{project_name} {messages['session_complete']}", style="bold magenta")
    console.print()


def print_git_status_section(config: Dict[str, Any]) -> None:
    """Git status section output"""
    messages = config['messages']
    git_config = config['git_check']

    if not git_config['enabled']:
        return

    has_changes, staged, modified, untracked = check_git_status()

    print_git_status(has_changes, staged, modified, untracked, messages)

    if has_changes and git_config['warn_uncommitted']:
        console.print(f"   [yellow]{messages['chromadb_reminder']}[/yellow]")
        console.print()


def print_chromadb_reminder(config: Dict[str, Any]) -> None:
    """ChromaDB Save Notification Output"""
    save_reminder = config['save_reminder']
    messages = config['messages']

    if not save_reminder['enabled']:
        return

    collection = save_reminder['collection']
    required_metadata = save_reminder['required_metadata']
    optional_metadata = save_reminder['optional_metadata']
    metadata_rules = save_reminder['metadata_rules']
    id_format = save_reminder['id_format']
    id_example = save_reminder['id_example']

    console.print(f"\n[bold cyan]{messages['chromadb_save']}[/bold cyan]")

    items = [
        ("Collection", collection),
        ("ID Format", id_format),
        ("ID Example", id_example),
    ]
    print_key_value_list(items, title=None)

    console.print("[cyan]Required Metadata:[/cyan]")
    for field in required_metadata:
        rule = metadata_rules.get(field, '')
        if rule:
            console.print(f"   [green]•[/green] {field}: [dim]{rule}[/dim]")
        else:
            console.print(f"   [green]•[/green] {field}")
    console.print()

    if optional_metadata:
        console.print("[cyan]Optional Metadata:[/cyan]")
        for field in optional_metadata:
            rule = metadata_rules.get(field, '')
            if rule:
                console.print(f"   [white]•[/white] {field}: [dim]{rule}[/dim]")
            else:
                console.print(f"   [white]•[/white] {field}")
        console.print()


def print_save_example(config: Dict[str, Any]) -> None:
    """ChromaDB Storage Example Output"""
    save_reminder = config['save_reminder']
    metadata_template = config['metadata_template']

    if not save_reminder['enabled']:
        return

    collection = save_reminder['collection']
    id_format = save_reminder['id_format']

    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')

    if 'code' in id_format.lower():
        id_prefix = 'chat_code_'
    else:
        id_prefix = 'chat_'

    timestamp = now.strftime('%Y%m%d_%H%M%S')
    actual_id = f"{id_prefix}{timestamp}"

    metadata_example: Dict[str, Any] = {
        "project": metadata_template['project'],
        "subproject": "core",
        "date": date_str,
        "type": "conversation",
        "summary": "<One-line summary of the work>",
    }

    if 'files' in metadata_template:
        metadata_example['files'] = ["example.py"]
    if 'tags' in metadata_template:
        metadata_example['tags'] = ["tag1", "tag2"]
    if 'status' in metadata_template:
        metadata_example['status'] = "completed"

    code = f"""chroma:chroma_add_documents(
    collection_name="{collection}",
    documents=["<Full conversation or task summary>"],
    ids=["{actual_id}"],
    metadatas=[{{
        "project": "{metadata_example['project']}",
        "subproject": "{metadata_example.get('subproject', 'core')}",
        "date": "{metadata_example['date']}",
        "type": "{metadata_example['type']}",
        "summary": "{metadata_example['summary']}","""

    if 'files' in metadata_example:
        code += f'\n        "files": {json.dumps(metadata_example["files"])},'
    if 'tags' in metadata_example:
        code += f'\n        "tags": {json.dumps(metadata_example["tags"])},'
    if 'status' in metadata_example:
        code += f'\n        "status": "{metadata_example["status"]}"'

    code += "\n    }]\n)"

    print_code_example(code, language="python", title="ChromaDB Save Example")


def print_completion_checks(config: Dict[str, Any]) -> None:
    """Print Completion Checklist"""
    checks = config['completion_checks']
    messages = config['messages']

    if not checks:
        return

    console.print(f"\n[bold cyan]{messages['completion_checks']}[/bold cyan]\n")
    table = create_completion_table(checks)
    console.print(table)
    console.print()


def print_metadata_template_section(config: Dict[str, Any]) -> None:
    """Metadata Template Section Output"""
    metadata_template = config['metadata_template']

    if not metadata_template:
        return

    print_metadata_template(metadata_template, title="Metadata Template")


def print_footer(config: Dict[str, Any]) -> None:
    """Session End Footer Output"""
    messages = config['messages']

    print_rule("", style="dim")
    console.print(f"[cyan]{messages['chromadb_reminder']}[/cyan]")
    console.print(f"[bold green]{messages['thanks']}[/bold green]")
    print_rule("", style="bold magenta")
    console.print()


def main():
    """Main Function"""
    try:
        config = load_config('post-session.json')

        print_header(config)
        print_git_status_section(config)
        print_chromadb_reminder(config)
        print_save_example(config)
        print_completion_checks(config)
        print_metadata_template_section(config)
        print_footer(config)

        sys.exit(0)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
