"""
Common utilities package for Claude Code hooks.

This package contains shared utilities used across different hook scripts:
- config: Configuration loading and management
- logger: Logging utilities with Sentry integration
- formatting: Rich terminal formatting utilities
- sentry: Sentry monitoring and error tracking
- servers: Server management utilities
"""

from .config import load_config, load_auto_compact_config, load_settings
from .logger import HookLogger
from .formatting import (
    console,
    print_rule,
    create_info_table,
    create_rules_table,
)
from .sentry import (
    init_sentry,
    capture_exception,
    capture_message,
    add_breadcrumb,
    flush,
)
from .servers import (
    get_server_status_internal,
    SERVER_CONFIG,
)

__all__ = [
    # Config
    'load_config',
    'load_auto_compact_config',
    'load_settings',

    # Logger
    'HookLogger',

    # Formatting
    'console',
    'print_rule',
    'create_info_table',
    'create_rules_table',

    # Sentry
    'init_sentry',
    'capture_exception',
    'capture_message',
    'add_breadcrumb',
    'flush',

    # Servers
    'get_server_status_internal',
    'SERVER_CONFIG',
]
