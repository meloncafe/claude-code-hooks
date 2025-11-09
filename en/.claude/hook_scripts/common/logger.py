#!/usr/bin/env python3
"""
Hook Logger - Hook Script Logging System
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

from .config import load_settings
from rich.console import Console

console = Console(stderr=True)

# Log level mapping
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}


class HookLogger:
    """Hook Script Logger"""

    def __init__(self, script_name: str):
        """
        Args:
            script_name: Script name (e.g., "session-start", "auto-compact")
        """
        self.script_name = script_name
        self.start_time = datetime.now()
        self.config = load_settings('logging')
        self.enabled = self.config.get('enabled', True)
        self.log_dir = self._get_log_dir()
        self.log_file = self.log_dir / f"{script_name}.log"

        # Load global settings for version and project info
        self.global_settings = load_settings()
        self.version = self.global_settings.get('version', '1.0.0')
        self.project = self.global_settings.get('project', 'unknown')
        self.description = self.global_settings.get('description', '')

        # Load additional config
        self.level = self.config.get('level', 'INFO').upper()
        self.log_format = self.config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handlers = self.config.get('handlers', ['file'])
        self.timestamp_format = self.config.get('timestamp_format', '%Y-%m-%d %H:%M:%S')
        self.include_level = self.config.get('include_level', True)
        self.include_script_name = self.config.get('include_script_name', True)

        # Rotation config
        rotation_config = self.config.get('rotation', {})
        self.rotation_enabled = rotation_config.get('enabled', True)
        self.max_size_mb = rotation_config.get('max_size_mb', 10)

    def _get_log_dir(self) -> Path:
        """Return and Create Log Directory Path"""
        project_root = self._find_project_root()
        log_dir_name = self.config.get('log_dir', '.claude/logs')

        if project_root:
            log_dir = project_root / log_dir_name
        else:
            log_dir = Path.cwd() / log_dir_name

        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def _find_project_root(self) -> Optional[Path]:
        """Finding the Project Root"""
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
        if project_dir:
            project_path = Path(project_dir)
            if project_path.exists():
                return project_path

        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / ".claude").exists():
                return parent

        return None

    def _should_log(self, level: str) -> bool:
        """Check if message should be logged based on level"""
        if not self.enabled:
            return False

        message_level = LOG_LEVELS.get(level.upper(), LOG_LEVELS['INFO'])
        config_level = LOG_LEVELS.get(self.level, LOG_LEVELS['INFO'])

        return message_level >= config_level

    def log_start(self, **kwargs) -> None:
        """Script Start Log"""
        if not self._should_log('INFO'):
            return

        log_entry = {
            "timestamp": self.start_time.isoformat(),
            "event": "start",
            "script": self.script_name,
            "project": self.project,
            "version": self.version,
            "cwd": str(Path.cwd()),
            **kwargs
        }
        self._write_log(log_entry, level='INFO')

    def log_end(self, success: bool = True, **kwargs) -> None:
        """Script termination log"""
        level = 'INFO' if success else 'ERROR'
        if not self._should_log(level):
            return

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        log_entry = {
            "timestamp": end_time.isoformat(),
            "event": "end",
            "script": self.script_name,
            "success": success,
            "duration_seconds": round(duration, 3),
            **kwargs
        }
        self._write_log(log_entry, level=level)

    def log_info(self, message: str, **kwargs) -> None:
        """Information Log"""
        if not self._should_log('INFO'):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "info",
            "script": self.script_name,
            "message": message,
            **kwargs
        }
        self._write_log(log_entry, level='INFO')

    def log_error(self, error: str, **kwargs) -> None:
        """Error Log"""
        if not self._should_log('ERROR'):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "error",
            "script": self.script_name,
            "error": error,
            **kwargs
        }
        self._write_log(log_entry, level='ERROR')

    def log_warning(self, message: str, **kwargs) -> None:
        """Warning Log"""
        if not self._should_log('WARNING'):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "warning",
            "script": self.script_name,
            "message": message,
            **kwargs
        }
        self._write_log(log_entry, level='WARNING')

    def _write_log(self, log_entry: Dict[str, Any], level: str = 'INFO') -> None:
        """Log records (output varies by handler)"""
        try:
            # Check rotation before writing
            if self.rotation_enabled and 'file' in self.handlers:
                self._check_rotation()

            # Write to file handler (JSON format)
            if 'file' in self.handlers:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

            # Write to console handler (formatted)
            if 'console' in self.handlers:
                formatted_message = self._format_message(log_entry, level)
                console.print(formatted_message)

            # Write to Sentry handler
            if 'sentry' in self.handlers:
                self._write_to_sentry(log_entry, level)

        except Exception as e:
            console.print(f"[yellow]WARNING: Log write failed: {e}[/]")

    def _format_message(self, log_entry: Dict[str, Any], level: str) -> str:
        """Format log message according to config format string"""
        timestamp_str = datetime.fromisoformat(log_entry['timestamp']).strftime(self.timestamp_format)

        # Extract message content
        message_content = ''
        if 'message' in log_entry:
            message_content = log_entry['message']
        elif 'error' in log_entry:
            message_content = f"ERROR: {log_entry['error']}"
        elif 'event' in log_entry:
            message_content = log_entry['event']

        # Use Python logging format string if available
        if self.log_format and '%(' in self.log_format:
            # Build format dictionary compatible with Python logging
            format_dict = {
                'asctime': timestamp_str,
                'name': self.script_name,
                'levelname': level,
                'message': message_content,
                'script': self.script_name,
                'level': level,
                'timestamp': timestamp_str,
                'project': self.project,
                'version': self.version
            }

            # Apply format string (e.g., "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            return self.log_format % format_dict

        # Legacy format (when format string is not set)
        parts = []
        parts.append(timestamp_str)

        if self.include_script_name:
            parts.append(self.script_name)

        if self.include_level:
            parts.append(level)

        parts.append(message_content)

        return ' - '.join(parts)

    def _write_to_sentry(self, log_entry: Dict[str, Any], level: str) -> None:
        """Write log to Sentry"""
        try:
            # Import here to avoid circular imports
            from .sentry import capture_message, add_breadcrumb, _sentry_initialized
            import sentry_sdk

            if not _sentry_initialized:
                return

            # Add project description to Sentry context
            if self.description:
                sentry_sdk.set_context('project_info', {
                    'name': self.project,
                    'version': self.version,
                    'description': self.description
                })

            # Extract message
            message = ''
            if 'message' in log_entry:
                message = log_entry['message']
            elif 'error' in log_entry:
                message = log_entry['error']
            elif 'event' in log_entry:
                message = f"{log_entry['event']}: {self.script_name}"

            # Map log level to Sentry level
            sentry_level_map = {
                'DEBUG': 'debug',
                'INFO': 'info',
                'WARNING': 'warning',
                'ERROR': 'error',
                'CRITICAL': 'fatal'
            }
            sentry_level = sentry_level_map.get(level, 'info')

            # Send to Sentry based on level
            if level in ['ERROR', 'CRITICAL']:
                # Send as message for errors
                capture_message(
                    message,
                    level=sentry_level,
                    context={
                        'log_entry': log_entry,
                        'script': self.script_name,
                        'project': self.project,
                        'version': self.version
                    }
                )
            else:
                # Send as breadcrumb for info/debug/warning
                add_breadcrumb(
                    message=message,
                    category='log',
                    level=sentry_level,
                    data={
                        'script': self.script_name,
                        'event': log_entry.get('event', ''),
                        'project': self.project
                    }
                )
        except Exception:
            # Sentry logging failure should not break the script
            pass

    def _check_rotation(self) -> None:
        """Check if log file needs rotation based on size"""
        if not self.log_file.exists():
            return

        file_size_mb = self.log_file.stat().st_size / (1024 * 1024)

        if file_size_mb >= self.max_size_mb:
            # Rotate: rename current file and start new one
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            rotated_file = self.log_file.with_suffix(f'.{timestamp}.log')
            self.log_file.rename(rotated_file)

            # Clean up old rotated files
            rotate_logs(self.log_dir, max_files=self.config.get('rotation', {}).get('max_files', 10))


def rotate_logs(log_dir: Optional[Path] = None, max_files: Optional[int] = None) -> None:
    """
    Delete Old Log Files

    Args:
        log_dir: Log directory (None means auto-detect)
        max_files: Maximum number of files to retain per script (None means load from settings)
    """
    config = load_settings('logging')

    # Check if rotation is enabled
    rotation_config = config.get('rotation', {})
    if not rotation_config.get('enabled', True):
        return

    if max_files is None:
        max_files = rotation_config.get('max_files', 10)

    if log_dir is None:
        project_root = None
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
        if project_dir:
            project_root = Path(project_dir)
        else:
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                if (parent / ".claude").exists():
                    project_root = parent
                    break

        log_dir_name = config.get('log_dir', '.claude/logs')
        if project_root:
            log_dir = project_root / log_dir_name
        else:
            log_dir = Path.cwd() / log_dir_name

    if not log_dir.exists():
        return

    log_files_by_name: Dict[str, list] = {}
    for log_file in log_dir.glob("*.log"):
        script_name = log_file.stem
        if script_name not in log_files_by_name:
            log_files_by_name[script_name] = []
        log_files_by_name[script_name].append(log_file)

    for script_name, files in log_files_by_name.items():
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for old_file in files[max_files:]:
            try:
                old_file.unlink()
            except Exception:
                pass


def get_recent_logs(script_name: str, limit: int = 50) -> list:
    """
    Recent Log Query

    Args:
        script_name: Script name
        limit: Maximum number of entries to retrieve

    Returns:
        List of log entries (most recent first)
    """
    config = load_settings('logging')

    project_root = None
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        project_root = Path(project_dir)
    else:
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / ".claude").exists():
                project_root = parent
                break

    log_dir_name = config.get('log_dir', '.claude/logs')
    if project_root:
        log_file = project_root / log_dir_name / f"{script_name}.log"
    else:
        log_file = Path.cwd() / log_dir_name / f"{script_name}.log"

    if not log_file.exists():
        return []

    logs = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

    return logs
