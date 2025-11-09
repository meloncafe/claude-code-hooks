#!/usr/bin/env python3
"""
Example Project - Timestamp validation script.
Prevents incorrect dates in documentation, commits, and changelogs.

Can be used as a pre-commit hook or standalone validator.
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console(stderr=True)


def load_git_hooks_config() -> Dict[str, Any]:
    """
    Load git-hooks.json configuration file.
    """
    candidates = [
        Path.cwd() / ".claude" / "config" / "git-hooks.json",
        Path.home() / ".claude" / "config" / "git-hooks.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            try:
                with open(candidate, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

    # Default fallback configuration
    return {
        "timestamp_validation": {
            "enabled": True,
            "validate_extensions": [".md", ".rst", ".txt", ".yaml", ".yml", ".json"],
            "special_files": ["CHANGELOG.md", "CHANGELOG.rst", "HISTORY.md", "RELEASES.md"],
            "min_date_offset_days": -365,
            "max_date_offset_days": 30,
            "date_formats": ["%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y", "%B %d, %Y"]
        }
    }


class TimestampValidator:
    """
    Timestamp accuracy validator.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with configuration.

        Args:
            config: Configuration from git-hooks.json
        """
        self.current_date = datetime.now()
        self.warnings: List[str] = []

        # Load configuration from git-hooks.json or use defaults
        if config is None:
            config = load_git_hooks_config()

        timestamp_config = config.get('timestamp_validation', {})

        # Extract configuration values
        self.enabled = timestamp_config.get('enabled', True)
        validate_extensions = timestamp_config.get('validate_extensions', [])
        special_files = timestamp_config.get('special_files', [])
        self.min_date_offset_days = timestamp_config.get('min_date_offset_days', -365)
        self.max_date_offset_days = timestamp_config.get('max_date_offset_days', 30)
        date_formats = timestamp_config.get('date_formats', [])

        # Build validate file patterns from extensions
        self.validate_files = [r'CHANGELOG.*', r'docs/.*', r'.*README.*']
        for ext in validate_extensions:
            self.validate_files.append(r'.*\{ext}$'.replace('{ext}', re.escape(ext)))

        # Add special files
        for special_file in special_files:
            self.validate_files.append(re.escape(special_file))

        # Exclude patterns (hardcoded as they are environment-specific)
        self.exclude_files = [
            r'node_modules/', r'\.git/', r'__pycache__/', r'\.venv/', r'venv/'
        ]

        # Build date patterns from config
        self.date_patterns = []
        for date_format in date_formats:
            if date_format == "%Y-%m-%d":
                self.date_patterns.append((date_format, r'\d{4}-\d{2}-\d{2}'))
                self.date_patterns.append((date_format, r'\d{4}-\d{1,2}-\d{1,2}'))
            elif date_format == "%m/%d/%Y":
                self.date_patterns.append((date_format, r'\d{1,2}/\d{1,2}/\d{4}'))
            elif date_format == "%d.%m.%Y":
                self.date_patterns.append((date_format, r'\d{1,2}\.\d{1,2}\.\d{4}'))
            elif date_format == "%B %d, %Y":
                self.date_patterns.append((date_format, r'\w+ \d{1,2}, \d{4}'))

    def is_date_reasonable(self, date_str: str, date_format: str) -> bool:
        """
        Check if date is within reasonable range.
        """
        try:
            date_obj = datetime.strptime(date_str, date_format)

            # Use configured date offsets
            min_date = self.current_date + timedelta(days=self.min_date_offset_days)
            max_date = self.current_date + timedelta(days=self.max_date_offset_days)

            return min_date <= date_obj <= max_date
        except ValueError:
            return True

    def find_dates_in_content(self, content: str) -> List[Tuple[str, str]]:
        """
        Find all date patterns in content.
        """
        found_dates = []
        for date_format, pattern in self.date_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                found_dates.append((match, date_format))
        return found_dates

    def validate_changelog(self, content: str, filepath: str) -> List[str]:
        """CHANGELOG File Verification"""
        warnings = []

        if not re.search(r'CHANGELOG', filepath, re.IGNORECASE):
            return warnings

        version_pattern = r'## \[[\d.]+\] - (\d{4}-\d{2}-\d{2})'
        matches = re.findall(version_pattern, content)

        for date_str in matches:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                if date_obj.date() > self.current_date.date():
                    warnings.append(
                        f"[DATE] CHANGELOG: Future date '{date_str}' detected. "
                        f"Use today's date: {self.current_date.strftime('%Y-%m-%d')}"
                    )

                if date_obj < self.current_date - timedelta(days=365):
                    warnings.append(
                        f"[DATE] CHANGELOG: Very old date '{date_str}'. "
                        "Isn't that a mistake?"
                    )
            except ValueError:
                pass

        return warnings

    def validate_file_content(self, filepath: str) -> List[str]:
        """File Content Verification"""
        warnings = []

        # Check if validation is enabled
        if not self.enabled:
            return warnings

        if not any(re.match(pattern, filepath) for pattern in self.validate_files):
            return warnings

        if any(re.search(pattern, filepath) for pattern in self.exclude_files):
            return warnings

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, UnicodeDecodeError, PermissionError):
            return warnings

        changelog_warnings = self.validate_changelog(content, filepath)
        warnings.extend(changelog_warnings)

        found_dates = self.find_dates_in_content(content)

        suspicious_dates = []
        for date_str, date_format in found_dates:
            if not self.is_date_reasonable(date_str, date_format):
                suspicious_dates.append(date_str)

        if suspicious_dates:
            warnings.append(
                f"[DATE] {filepath}: Suspicious date detected: {', '.join(set(suspicious_dates))}"
                f"   Current date: {self.current_date.strftime('%Y-%m-%d')}"
            )

        return warnings

    def suggest_timestamps(self) -> dict:
        """Current Timestamp Proposal"""
        return {
            'iso_date': self.current_date.strftime('%Y-%m-%d'),
            'iso_datetime': self.current_date.strftime('%Y-%m-%d %H:%M:%S'),
            'readable': self.current_date.strftime('%A, %B %d, %Y'),
            'changelog': self.current_date.strftime('%Y-%m-%d'),
            'log_format': self.current_date.strftime('%Y-%m-%d %H:%M:%S'),
        }


def validate_commit_message(message: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Validate dates in commit message.

    Args:
        message: Commit message to validate
        config: Configuration from git-hooks.json

    Returns:
        List of warning messages
    """
    validator = TimestampValidator(config)

    # Check if validation is enabled
    if not validator.enabled:
        return []

    warnings = []

    found_dates = validator.find_dates_in_content(message)

    for date_str, date_format in found_dates:
        if not validator.is_date_reasonable(date_str, date_format):
            warnings.append(
                f"[DATE] Commit messages containing suspicious dates: '{date_str}'. "
                f"   Current date: {validator.current_date.strftime('%Y-%m-%d')}"
            )

    return warnings


def main():
    """
    Main function for timestamp validation.
    """
    # Load configuration once for all validations
    config = load_git_hooks_config()
    validator = TimestampValidator(config)

    # Check if validation is enabled
    if not validator.enabled:
        sys.exit(0)

    all_warnings = []

    if len(sys.argv) >= 2:
        commit_msg_file = sys.argv[1]

        try:
            with open(commit_msg_file, 'r', encoding='utf-8') as f:
                commit_message = f.read()

            warnings = validate_commit_message(commit_message, config)
            all_warnings.extend(warnings)
        except (FileNotFoundError, UnicodeDecodeError):
            pass
    else:
        project_root = Path.cwd()

        for filepath in project_root.rglob('*'):
            if filepath.is_file():
                file_warnings = validator.validate_file_content(str(filepath))
                all_warnings.extend(file_warnings)

    if all_warnings:
        console.print("[yellow bold]TIMESTAMP VALIDATION WARNINGS:[/]")
        for warning in all_warnings:
            console.print(f"  [yellow]-[/] {warning}")

        timestamps = validator.suggest_timestamps()

        table = Table(title="Current Timestamp Reference", show_header=True, header_style="bold cyan", box=box.SIMPLE)
        table.add_column("Format", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("ISO Date", timestamps['iso_date'])
        table.add_row("Readable", timestamps['readable'])
        table.add_row("CHANGELOG", timestamps['changelog'])
        table.add_row("Log Format", timestamps['log_format'])

        console.print()
        console.print(table)

    sys.exit(0)


if __name__ == "__main__":
    main()
