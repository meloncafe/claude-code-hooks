#!/usr/bin/env python3
"""
Secret Scanner Hook (Improved Version)
Prevents accidental exposure of secrets, API keys, and sensitive information.
Optimized for Claude Code hooks system.
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from common.config import load_security_config

console = Console(stderr=True)

# Load configuration from settings file
_CONFIG = load_security_config()
MAX_FILE_SIZE = _CONFIG.get('max_file_size', 1048576)
MAX_ISSUES_TO_SHOW = _CONFIG.get('max_issues_to_show', 10)


def load_patterns_from_config(pattern_list: List[Dict[str, str]]) -> List[str]:
    """Convert pattern configuration to list of regex patterns."""
    return [p['pattern'] for p in pattern_list if 'pattern' in p]


# Load patterns from configuration
HIGH_SEVERITY_PATTERNS = {
    'configured': load_patterns_from_config(_CONFIG.get('high_severity_patterns', []))
}

MEDIUM_SEVERITY_PATTERNS = {
    'configured': load_patterns_from_config(_CONFIG.get('medium_severity_patterns', []))
}

ALLOWED_PATTERNS = load_patterns_from_config(_CONFIG.get('allowed_patterns', []))


def is_binary_content(content):
    """Check if content is binary."""
    return '\0' in content


def should_skip_file(file_path):
    """Determine if file should be skipped entirely."""
    skip_extensions = _CONFIG['skip_extensions']
    skip_dirs = _CONFIG['skip_directories']

    if any(file_path.endswith(ext) for ext in skip_extensions):
        return True

    if any(dir_name in file_path for dir_name in skip_dirs):
        return True

    return False


def is_allowed_context(content, match_start, match_end):
    """Check if the match is in an allowed context (reduces false positives)."""
    context_start = max(0, match_start - 100)
    context_end = min(len(content), match_end + 100)
    context = content[context_start:context_end]

    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, context, re.IGNORECASE):
            return True

    lines_before = content[:match_start].split('\n')
    if lines_before:
        last_line = lines_before[-1].strip()
        if any(last_line.startswith(prefix) for prefix in ['//', '#', '*', '<!--', '/*']):
            return True

    test_indicators = [
        'describe(', 'it(', 'test(', 'expect(', 'assert',
        'should', 'fixture', 'mock', 'stub', 'spy'
    ]
    if any(indicator in context for indicator in test_indicators):
        return True

    doc_indicators = ['@example', 'Example:', '```', 'e.g.', 'for example']
    if any(indicator in context for indicator in doc_indicators):
        return True

    return False


def scan_content(content, file_path, severity_level='all'):
    """Scan content for potential secrets."""
    issues = []

    if is_binary_content(content):
        return issues

    if len(content) > MAX_FILE_SIZE:
        return issues

    if should_skip_file(file_path):
        return issues

    patterns_to_check = {}
    if severity_level in ['high', 'all']:
        patterns_to_check.update(HIGH_SEVERITY_PATTERNS)
    if severity_level in ['medium', 'all']:
        patterns_to_check.update(MEDIUM_SEVERITY_PATTERNS)

    for category, patterns in patterns_to_check.items():
        for pattern in patterns:
            try:
                matches = list(re.finditer(pattern, content, re.MULTILINE))
            except re.error:
                continue

            for match in matches:
                if is_allowed_context(content, match.start(), match.end()):
                    continue

                line_num = content[:match.start()].count('\n') + 1

                secret_value = match.group(0)
                if len(secret_value) > 20:
                    redacted = secret_value[:10] + '...[REDACTED]'
                else:
                    redacted = '[REDACTED]'

                severity = 'high' if category in HIGH_SEVERITY_PATTERNS else 'medium'

                issues.append({
                    'line': line_num,
                    'category': category,
                    'value': redacted,
                    'severity': severity
                })

    return issues


def check_gitignore():
    """Check if .gitignore properly excludes sensitive files."""
    issues = []
    gitignore_path = Path('.gitignore')

    if not gitignore_path.exists():
        issues.append({
            'type': 'gitignore_missing',
            'message': 'No .gitignore file found. Create one to prevent committing sensitive files.',
            'severity': 'medium'
        })
        return issues

    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()

    required_patterns = [
        '.env',
        '*.pem',
        '*.key',
    ]

    recommended_patterns = [
        '.env.local',
        '.env.*.local',
        'config/secrets.yml',
        'config/database.yml',
    ]

    missing_required = []
    missing_recommended = []

    for pattern in required_patterns:
        if pattern not in gitignore_content:
            if pattern.startswith('.env') and '.env*' in gitignore_content:
                continue
            missing_required.append(pattern)

    for pattern in recommended_patterns:
        if pattern not in gitignore_content:
            if pattern.endswith('.local') and '*.local' in gitignore_content:
                continue
            if pattern.startswith('.env') and '.env*' in gitignore_content:
                continue
            missing_recommended.append(pattern)

    if missing_required:
        issues.append({
            'type': 'gitignore_missing_required',
            'message': f"Add to .gitignore: {', '.join(missing_required)}",
            'severity': 'high'
        })

    if missing_recommended:
        issues.append({
            'type': 'gitignore_missing_recommended',
            'message': f"Consider adding to .gitignore: {', '.join(missing_recommended)}",
            'severity': 'low'
        })

    return issues


def check_env_file_commit(files):
    """Check if .env files are being committed."""
    env_files = [f for f in files if f.endswith('.env') or '.env.' in f]
    env_files = [f for f in env_files
                 if not f.endswith('.example')
                 and not f.endswith('.sample')
                 and not f.endswith('.template')]

    if env_files:
        return [{
            'type': 'env_file_commit',
            'files': env_files,
            'severity': 'critical'
        }]

    return []


def format_output(all_issues):
    """Format issues for output with clear severity levels."""
    if not all_issues:
        return None

    console.rule("[cyan bold]SECURITY SCAN RESULTS", style="cyan")

    blocking = False

    env_commits = [i for i in all_issues if isinstance(i, dict) and i.get('type') == 'env_file_commit']
    if env_commits:
        blocking = True
        msg = "\n🚨 CRITICAL: .env file commit detected\n"
        sys.stderr.write(msg)
        sys.stderr.flush()
        console.print("[red bold]CRITICAL: .env file commit detected[/]")
        for issue in env_commits:
            for f in issue['files']:
                console.print(f"  [red]X[/] {f}")
        console.print("[yellow]![/] Add these files to .gitignore immediately!")
        console.print()

    file_issues = [i for i in all_issues if isinstance(i, dict) and 'file' in i]
    high_severity_files = []
    medium_severity_files = []

    for file_data in file_issues:
        high = [i for i in file_data['issues'] if i['severity'] == 'high']
        medium = [i for i in file_data['issues'] if i['severity'] == 'medium']

        if high:
            high_severity_files.append((file_data['file'], high))
        if medium:
            medium_severity_files.append((file_data['file'], medium))

    if high_severity_files:
        blocking = True
        console.print("[red bold]HIGH SEVERITY: Sensitive information detected[/]")
        console.print()

        for file_path, issues in high_severity_files:
            table = Table(title=f"File: {file_path}", box=box.SIMPLE, show_header=True, header_style="bold red")
            table.add_column("Line", justify="right", style="cyan")
            table.add_column("Category", style="yellow")
            table.add_column("Value", style="red dim")

            for i, issue in enumerate(issues[:MAX_ISSUES_TO_SHOW], 1):
                category_name = issue['category'].replace('_', ' ').title()
                table.add_row(str(issue['line']), category_name, issue['value'])

            console.print(table)

            if len(issues) > MAX_ISSUES_TO_SHOW:
                console.print(f"[dim]... and {len(issues) - MAX_ISSUES_TO_SHOW} more[/]")
            console.print()

    if medium_severity_files:
        console.print("[yellow bold]MEDIUM SEVERITY: Suspicious sensitive information detected[/]")
        console.print()

        for file_path, issues in medium_severity_files:
            console.print(f"[cyan]File: {file_path}[/]")
            for i, issue in enumerate(issues[:3], 1):
                category_name = issue['category'].replace('_', ' ').title()
                console.print(f"  - Line {issue['line']}: {category_name}")

            if len(issues) > 3:
                console.print(f"  [dim]... and {len(issues) - 3} more[/]")
        console.print()

    gitignore_issues = [i for i in all_issues if isinstance(i, dict) and i.get('type', '').startswith('gitignore')]
    if gitignore_issues:
        console.print("[cyan bold].gitignore Suggestions:[/]")
        for issue in gitignore_issues:
            if issue['severity'] == 'high':
                blocking = True
                console.print(f"  [red]![/] {issue['message']}")
            else:
                console.print(f"  [yellow]-[/] {issue['message']}")
        console.print()

    best_practices = Panel(
        "[cyan]*[/] Use environment variables for sensitive data\n"
        "[cyan]*[/] Never commit .env files (add to .gitignore)\n"
        "[cyan]*[/] Use secret management services in production\n"
        "[cyan]*[/] Rotate exposed credentials immediately",
        title="[cyan bold]Security Best Practices",
        border_style="cyan"
    )
    console.print(best_practices)
    console.print()

    if blocking:
        console.print("[red bold]X Commit blocked due to security issues[/]")
        console.rule(style="red")
        return True
    else:
        console.print("[yellow bold]! Proceeding with warnings - please review[/]")
        console.rule(style="yellow")
        return False


def main():
    try:
        if not _CONFIG.get('enabled', True):
            sys.exit(0)

        input_data = json.load(sys.stdin)
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        if tool_name == 'bash_tool':
            command = tool_input.get('command', '')

            if 'git commit' in command or 'git add' in command:
                import subprocess

                result = subprocess.run(
                    ['git', 'diff', '--cached', '--name-only'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if not result.stdout:
                    sys.exit(0)

                files = result.stdout.strip().split('\n') if result.stdout else []
                all_issues = []

                env_issues = check_env_file_commit(files)
                if env_issues:
                    all_issues.extend(env_issues)

                gitignore_issues = check_gitignore()
                all_issues.extend(gitignore_issues)

                for file_path in files:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()

                            file_issues = scan_content(content, file_path, severity_level='all')
                            if file_issues:
                                all_issues.append({
                                    'file': file_path,
                                    'issues': file_issues
                                })
                        except Exception:
                            continue

                if all_issues:
                    should_block = format_output(all_issues)
                    if should_block:
                        sys.exit(2)

        elif tool_name in ['create_file', 'str_replace']:
            file_path = tool_input.get('path', '') or tool_input.get('file_path', '')

            if '.env' in file_path and not file_path.endswith('.example'):
                console.print(Panel(
                    ".env file editing detected. Ensure it's in .gitignore!",
                    title="[yellow bold]SECURITY ALERT",
                    border_style="yellow"
                ))

            content = ''
            if tool_name == 'create_file':
                content = tool_input.get('file_text', '') or tool_input.get('content', '')
            elif tool_name == 'str_replace':
                content = tool_input.get('new_str', '')

            if content:
                issues = scan_content(content, file_path, severity_level='high')

                if issues:
                    msg = "\n⚠️  SECURITY WARNING: Potential secrets detected\n"
                    sys.stderr.write(msg)
                    sys.stderr.flush()
                    console.print("[yellow bold]SECURITY WARNING: Potential secrets detected[/]")
                    seen_lines = set()
                    shown = 0
                    for issue in issues:
                        if issue['line'] not in seen_lines and shown < 3:
                            seen_lines.add(issue['line'])
                            category_name = issue['category'].replace('_', ' ').title()
                            console.print(f"  Line {issue['line']}: {category_name}")
                            shown += 1

                    console.print("[yellow]![/] Use environment variables instead of hardcoded secrets")

        sys.exit(0)

    except Exception as e:
        console.print(f"[red bold]Security scanner hook error: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
