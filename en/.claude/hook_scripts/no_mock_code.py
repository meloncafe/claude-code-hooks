#!/usr/bin/env python3
"""
No Mock Code Hook for Claude Code
Prevents mock/placeholder code from being committed.
"""
import json
import os
import re
import sys
from typing import List, Dict, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from common.config import load_code_quality_config

console = Console(stderr=True)

# Load configuration
_CONFIG = load_code_quality_config()
MAX_FILE_SIZE = _CONFIG.get('max_file_size', 1000000)

PLACEHOLDER_PATTERNS = _CONFIG.get('placeholder_patterns', [])
SEVERITY_MAPPING = _CONFIG.get('severity_mapping', {})
DOC_KEYWORDS = _CONFIG.get('doc_keywords', [])
SKIP_PATTERNS = _CONFIG.get('skip_patterns', [])


def is_documentation_context(line: str, lines: List[str], line_num: int) -> bool:
    """Check if line is within documentation context."""
    line_lower = line.lower()
    if any(keyword in line_lower for keyword in DOC_KEYWORDS):
        return True

    start = max(0, line_num - 5)
    end = min(len(lines), line_num + 5)

    before = '\n'.join(lines[start:line_num])
    triple_double = before.count('"""')
    triple_single = before.count("'''")

    if triple_double % 2 == 1 or triple_single % 2 == 1:
        return True

    for i in range(max(0, line_num - 10), line_num):
        if '/**' in lines[i]:
            for j in range(i, min(len(lines), line_num + 5)):
                if '*/' in lines[j]:
                    if i <= line_num <= j:
                        return True
                    break
            break

    stripped = line.strip()
    if stripped.startswith('#') and not any(kw in line for kw in ['TODO', 'FIXME', 'HACK', 'XXX']):
        return True

    return False


def is_in_comment(line: str) -> bool:
    """Check if line is a comment."""
    stripped = line.strip()
    return (
        stripped.startswith('//') or
        stripped.startswith('#') or
        stripped.startswith('*') or
        stripped.startswith('/*') or
        stripped.startswith('*/')
    )


def check_static_return_values(content: str, file_path: str, lines: List[str]) -> List[Dict]:
    """Check for functions that always return static values."""
    issues = []

    if any(pattern in file_path.lower() for pattern in SKIP_PATTERNS):
        return issues

    patterns = [
        (r'(?:function\s+\w+|const\s+\w+\s*=.*?)\s*\([^)]*\)\s*(?:=>|\{)[^{}]{0,100}return\s+["\'][^"\']+["\']', 'static_string'),
        (r'(?:function\s+\w+|const\s+\w+\s*=.*?)\s*\([^)]*\)\s*(?:=>|\{)[^{}]{0,100}return\s+\d+(?:\.\d+)?(?!\s*[+\-*/])', 'static_number'),
        (r'(?:function\s+\w+|const\s+\w+\s*=.*?)\s*\([^)]*\)\s*(?:=>|\{)[^{}]{0,100}return\s+(?:true|false|null|undefined)(?!\s*[&|?])',
         'static_bool'),
        (r'def\s+\w+\([^)]*\)[^:]*:\s*(?:\n\s+["\'].*?["\'])?\s*return\s+["\'][^"\']+["\']', 'static_string'),
        (r'def\s+\w+\([^)]*\)[^:]*:\s*(?:\n\s+["\'].*?["\'])?\s*return\s+\d+(?:\.\d+)?', 'static_number'),
    ]

    for pattern, pattern_type in patterns:
        matches = list(re.finditer(pattern, content, re.MULTILINE))
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1

            if line_num > len(lines):
                continue

            if is_documentation_context(lines[line_num - 1], lines, line_num):
                continue

            context_start = max(0, line_num - 5)
            context_end = min(len(lines), line_num + 3)
            context = '\n'.join(lines[context_start:context_end]).lower()

            if any(word in context for word in ['default', 'fallback', 'placeholder', 'initial']):
                continue

            issues.append({
                'line': line_num,
                'type': f'static_return_{pattern_type}',
                'content': lines[line_num - 1].strip()[:80],
                'severity': 'high'
            })

    return issues


def check_todo_without_implementation(content: str, lines: List[str]) -> List[Dict]:
    """Check for TODO comments without actual implementation."""
    issues = []

    for i in range(len(lines)):
        line = lines[i]

        if is_documentation_context(line, lines, i):
            continue

        if not re.search(r'(?://|#|/\*)\s*(?:TODO|FIXME|HACK|XXX)', line, re.IGNORECASE):
            continue

        j = i + 1
        while j < len(lines) and (not lines[j].strip() or is_in_comment(lines[j])):
            j += 1

        if j >= len(lines):
            continue

        next_code = lines[j].strip()

        placeholder_returns = [
            'return null', 'return undefined', 'return None',
            'return 0', 'return false', 'return []', 'return {}',
            'throw new Error', 'raise NotImplementedError',
            'pass', '...'
        ]

        if any(placeholder in next_code for placeholder in placeholder_returns):
            issues.append({
                'line': i + 1,
                'type': 'todo_no_impl',
                'content': line.strip()[:80],
                'severity': 'high'
            })

    return issues


def check_fake_async_operations(content: str, lines: List[str]) -> List[Dict]:
    """Check for fake async operations."""
    issues = []

    fake_async_patterns = [
        r'setTimeout\s*\([^,]+,\s*\d+\s*\)\s*;?\s*//?\s*(?:fake|mock|simulate|delay)',
        r'new\s+Promise\s*\(\s*resolve\s*=>\s*setTimeout\s*\(\s*resolve\s*,\s*\d+\s*\)',
        r'await\s+new\s+Promise\s*\(\s*resolve\s*=>\s*setTimeout',
        r'time\.sleep\s*\(\s*\d+\s*\)\s*#.*(?:fake|mock|simulate)',
    ]

    for pattern in fake_async_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1

            if line_num > len(lines):
                continue

            if is_documentation_context(lines[line_num - 1], lines, line_num):
                continue

            issues.append({
                'line': line_num,
                'type': 'fake_async',
                'content': lines[line_num - 1].strip()[:80],
                'severity': 'medium'
            })

    return issues


def check_placeholder_content(content: str, file_path: str, lines: List[str]) -> List[Dict]:
    """Check for placeholder content in code."""
    issues = []

    if any(pattern in file_path.lower() for pattern in SKIP_PATTERNS):
        return issues

    for category, patterns in PLACEHOLDER_PATTERNS.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1

                if line_num > len(lines):
                    continue

                if is_in_comment(lines[line_num - 1]):
                    continue

                if is_documentation_context(lines[line_num - 1], lines, line_num):
                    continue

                issues.append({
                    'line': line_num,
                    'type': f'placeholder_{category}',
                    'content': match.group(0)[:60],
                    'severity': SEVERITY_MAPPING.get(category, 'medium')
                })

    return issues


def check_commented_real_code(content: str, lines: List[str]) -> List[Dict]:
    """Check for commented out real code with temporary implementations."""
    issues = []

    patterns = [
        r'//\s*(?:const|let|var)\s+\w+\s*=\s*await\s+\w+\.(?:query|find|fetch).*?\n\s*(?:const|let|var)\s+\w+\s*=\s*\[',
        r'//\s*\w+\.(?:get|post|put|delete)\(.*?\n\s*return\s*\{',
        r'#\s*\w+\s*=\s*(?:await\s+)?db\.\w+.*?\n\s*\w+\s*=\s*\[',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1

            if line_num > len(lines):
                continue

            if is_documentation_context(lines[line_num - 1], lines, line_num):
                continue

            snippet = match.group(0).replace('\n', ' ')[:80] + '...'
            issues.append({
                'line': line_num,
                'type': 'commented_real_code',
                'content': snippet,
                'severity': 'medium'
            })

    return issues


def should_skip_file(file_path: str) -> bool:
    """Determine if file should be skipped."""
    code_extensions = ['.js', '.ts', '.jsx', '.tsx', '.py', '.java', '.go', '.rb', '.php', '.cs', '.cpp', '.c']
    if not any(file_path.endswith(ext) for ext in code_extensions):
        return True

    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return True

    if any(pattern in file_path.lower() for pattern in SKIP_PATTERNS):
        return True

    return False


def analyze_file(file_path: str) -> List[Dict]:
    """Analyze a single file for mock/placeholder code."""
    if should_skip_file(file_path):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return []

    lines = content.split('\n')

    issues = []
    issues.extend(check_placeholder_content(content, file_path, lines))
    issues.extend(check_static_return_values(content, file_path, lines))
    issues.extend(check_todo_without_implementation(content, lines))
    issues.extend(check_fake_async_operations(content, lines))
    issues.extend(check_commented_real_code(content, lines))

    return issues


def format_issues_output(all_issues: List[Tuple[str, List[Dict]]]) -> None:
    """Format and print issues."""
    console.rule("[red bold]MOCK/PLACEHOLDER CODE DETECTED", style="red")

    for file_path, issues in all_issues:
        high_severity = [i for i in issues if i['severity'] == 'high']
        medium_severity = [i for i in issues if i['severity'] == 'medium']

        if high_severity:
            msg = f"\n🚨 CRITICAL: Mock/placeholder code in {file_path}\n"
            sys.stderr.write(msg)
            sys.stderr.flush()
            console.print(f"\n[red bold]CRITICAL: {file_path}[/]")

            table = Table(show_header=True, header_style="bold red", box=box.SIMPLE)
            table.add_column("Line", justify="right", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Content", style="red dim")

            for issue in high_severity[:5]:
                type_name = issue['type'].replace('_', ' ').title()
                table.add_row(str(issue['line']), type_name, issue['content'][:50])

            console.print(table)

            if len(high_severity) > 5:
                console.print(f"[dim]... and {len(high_severity) - 5} more[/]")

        if medium_severity:
            msg = f"\n⚠️  WARNING: Potential issues in {file_path}\n"
            sys.stderr.write(msg)
            sys.stderr.flush()
            console.print(f"\n[yellow bold]WARNING: {file_path}[/]")
            for issue in medium_severity[:3]:
                type_name = issue['type'].replace('_', ' ').title()
                console.print(f"  Line {issue['line']}: {type_name}")
            if len(medium_severity) > 3:
                console.print(f"  [dim]... and {len(medium_severity) - 3} more[/]")

    suggestions = Panel(
        "[cyan]*[/] Replace placeholder data with real implementation\n"
        "[cyan]*[/] Implement TODO items or create tracking issues\n"
        "[cyan]*[/] Remove fake delays and use actual operations",
        title="[cyan bold]SUGGESTIONS",
        border_style="cyan"
    )
    console.print()
    console.print(suggestions)


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        if tool_name != 'Bash':
            sys.exit(0)

        command = tool_input.get('command', '')
        if 'git commit' not in command:
            sys.exit(0)

        import subprocess
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True
        )

        if not result.stdout:
            sys.exit(0)

        files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]

        all_issues = []
        for file_path in files:
            if not os.path.exists(file_path):
                continue

            issues = analyze_file(file_path)
            if issues:
                all_issues.append((file_path, issues))

        if all_issues:
            format_issues_output(all_issues)

            has_high_severity = any(
                any(i['severity'] == 'high' for i in issues)
                for _, issues in all_issues
            )

            if has_high_severity:
                sys.exit(2)

        sys.exit(0)

    except Exception as e:
        console.print(f"[red bold]no-mock-code hook error: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
