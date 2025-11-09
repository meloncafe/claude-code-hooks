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
    git-hooks.json 설정 파일 로드.
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
    타임스탬프 정확성 검증기.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with configuration.
        설정으로 검증기 초기화.

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
        날짜가 합리적인 범위인지 확인.
        """
        try:
            date_obj = datetime.strptime(date_str, date_format)

            # Use configured date offsets
            min_date = self.current_date + timedelta(days=self.min_date_offset_days)
            max_date = self.current_date + timedelta(days=self.max_date_offset_days)

            return min_date <= date_obj <= max_date
        except ValueError:
            return True  # 파싱 실패 시 건너뛰기

    def find_dates_in_content(self, content: str) -> List[Tuple[str, str]]:
        """
        Find all date patterns in content.
        콘텐츠에서 모든 날짜 패턴 찾기.
        """
        found_dates = []
        for date_format, pattern in self.date_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                found_dates.append((match, date_format))
        return found_dates

    def validate_changelog(self, content: str, filepath: str) -> List[str]:
        """CHANGELOG 파일 검증"""
        warnings = []

        if not re.search(r'CHANGELOG', filepath, re.IGNORECASE):
            return warnings

        # 버전 헤더 날짜 패턴: ## [version] - YYYY-MM-DD
        version_pattern = r'## \[[\d.]+\] - (\d{4}-\d{2}-\d{2})'
        matches = re.findall(version_pattern, content)

        for date_str in matches:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                # 미래 날짜 체크
                if date_obj.date() > self.current_date.date():
                    warnings.append(
                        f"[DATE] CHANGELOG: 미래 날짜 '{date_str}' 발견. "
                        f"오늘 날짜 사용: {self.current_date.strftime('%Y-%m-%d')}"
                    )

                # 너무 오래된 날짜 체크 (1년 이상 전)
                if date_obj < self.current_date - timedelta(days=365):
                    warnings.append(
                        f"[DATE] CHANGELOG: 매우 오래된 날짜 '{date_str}'. "
                        "실수는 아닌가요?"
                    )
            except ValueError:
                pass

        return warnings

    def validate_file_content(self, filepath: str) -> List[str]:
        """파일 내용 검증"""
        warnings = []

        # Check if validation is enabled
        if not self.enabled:
            return warnings

        # 검증 대상 파일인지 확인
        if not any(re.match(pattern, filepath) for pattern in self.validate_files):
            return warnings

        # 제외 파일인지 확인
        if any(re.search(pattern, filepath) for pattern in self.exclude_files):
            return warnings

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, UnicodeDecodeError, PermissionError):
            return warnings

        # CHANGELOG 특별 검증
        changelog_warnings = self.validate_changelog(content, filepath)
        warnings.extend(changelog_warnings)

        # 일반 날짜 검증
        found_dates = self.find_dates_in_content(content)

        # 과거 또는 미래의 의심스러운 날짜만 경고
        suspicious_dates = []
        for date_str, date_format in found_dates:
            if not self.is_date_reasonable(date_str, date_format):
                suspicious_dates.append(date_str)

        if suspicious_dates:
            warnings.append(
                f"[DATE] {filepath}: 의심스러운 날짜 발견: {', '.join(set(suspicious_dates))}"
                f"   현재 날짜: {self.current_date.strftime('%Y-%m-%d')}"
            )

        return warnings

    def suggest_timestamps(self) -> dict:
        """현재 타임스탬프 제안"""
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
    커밋 메시지의 날짜 검증.

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
                f"[DATE] 커밋 메시지에 의심스러운 날짜 포함: '{date_str}'. "
                f"   현재 날짜: {validator.current_date.strftime('%Y-%m-%d')}"
            )

    return warnings


def main():
    """
    Main function for timestamp validation.
    타임스탬프 검증 메인 함수.
    """
    # Load configuration once for all validations
    config = load_git_hooks_config()
    validator = TimestampValidator(config)

    # Check if validation is enabled
    if not validator.enabled:
        sys.exit(0)

    all_warnings = []

    # Git hook으로 사용될 때
    if len(sys.argv) >= 2:
        commit_msg_file = sys.argv[1]

        # 커밋 메시지 검증
        try:
            with open(commit_msg_file, 'r', encoding='utf-8') as f:
                commit_message = f.read()

            warnings = validate_commit_message(commit_message, config)
            all_warnings.extend(warnings)
        except (FileNotFoundError, UnicodeDecodeError):
            pass
    else:
        # 독립 실행: 현재 디렉토리의 모든 파일 검증
        project_root = Path.cwd()

        for filepath in project_root.rglob('*'):
            if filepath.is_file():
                file_warnings = validator.validate_file_content(str(filepath))
                all_warnings.extend(file_warnings)

    # 경고 출력
    if all_warnings:
        console.print("[yellow bold]TIMESTAMP VALIDATION WARNINGS:[/]")
        for warning in all_warnings:
            console.print(f"  [yellow]-[/] {warning}")

        # 현재 타임스탬프 제안
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

    # 경고만 있으므로 항상 성공 (차단하지 않음)
    sys.exit(0)


if __name__ == "__main__":
    main()
