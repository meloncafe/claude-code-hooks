#!/usr/bin/env python3
"""
Configuration Utility for Claude Code Hooks

Centralized configuration loading with caching and multiple path support.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List


# Global cache for loaded configurations
_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}


def get_config_paths(config_name: str) -> List[Path]:
    """
    Get candidate paths for configuration file.

    Args:
        config_name: Configuration file name (e.g., 'settings.json', 'security.json')

    Returns:
        List of candidate paths in priority order
    """
    return [
        Path.cwd() / ".claude" / "config" / config_name,
        Path(__file__).parent.parent / "config" / config_name,
        Path.home() / ".claude" / "config" / config_name,
    ]


def load_config(
    config_name: str,
    section: Optional[str] = None,
    use_cache: bool = True,
    defaults: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Load configuration from JSON file with caching support.

    Args:
        config_name: Configuration file name (e.g., 'settings.json')
        section: Optional section name to extract from config
        use_cache: Whether to use cached configuration
        defaults: Default values if config file not found

    Returns:
        Configuration dictionary

    Examples:
        # Load entire settings.json
        config = load_config('settings.json')

        # Load specific section from settings.json
        sentry_config = load_config('settings.json', section='sentry')

        # Load with custom defaults
        config = load_config('custom.json', defaults={'enabled': True})
    """
    # Check cache first
    cache_key = f"{config_name}:{section or ''}"
    if use_cache and cache_key in _CONFIG_CACHE:
        return _CONFIG_CACHE[cache_key]

    # Try to load from candidate paths
    for candidate in get_config_paths(config_name):
        if candidate.exists():
            try:
                with open(candidate, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                    # Extract section if specified
                    if section:
                        config = config.get(section, defaults or {})

                    # Cache the result
                    if use_cache:
                        _CONFIG_CACHE[cache_key] = config

                    return config

            except (json.JSONDecodeError, IOError):
                continue

    # Return defaults if no config found
    return defaults or {}


def clear_cache(config_name: Optional[str] = None) -> None:
    """
    Clear configuration cache.

    Args:
        config_name: Specific config to clear, or None to clear all
    """
    global _CONFIG_CACHE

    if config_name is None:
        _CONFIG_CACHE.clear()
    else:
        # Clear all cache entries for this config
        keys_to_remove = [k for k in _CONFIG_CACHE.keys() if k.startswith(config_name)]
        for key in keys_to_remove:
            del _CONFIG_CACHE[key]


def load_settings(section: Optional[str] = None) -> Dict[str, Any]:
    """
    Load settings.json configuration.

    Args:
        section: Optional section name (e.g., 'sentry', 'logging')

    Returns:
        Configuration dictionary
    """
    defaults = {
        "version": "1.0.0",
        "project": "example_project"
    } if section is None else {}

    return load_config('settings.json', section=section, defaults=defaults)


def load_security_config() -> Dict[str, Any]:
    """
    Load security.json configuration for secret-scanner.

    Returns:
        Secret scanner configuration
    """
    return load_config('security.json', section='secret_scanner', defaults={
        "enabled": True,
        "max_file_size": 1048576
    })


def load_code_quality_config() -> Dict[str, Any]:
    """
    Load code-quality.json configuration for no-mock-code.

    Returns:
        Code quality configuration
    """
    return load_config('code-quality.json', section='no_mock_code', defaults={
        "enabled": True,
        "max_file_size": 1000000
    })


def load_auto_compact_config() -> Dict[str, Any]:
    """
    Load auto-compact.json configuration.

    Returns:
        Auto-compact configuration
    """
    return load_config('auto-compact.json', defaults={
        "enabled": True
    })


def get_config_value(
    config_name: str,
    key_path: str,
    default: Any = None,
    section: Optional[str] = None
) -> Any:
    """
    Get specific value from configuration using dot notation.

    Args:
        config_name: Configuration file name
        key_path: Dot-separated key path (e.g., 'sentry.dsn', 'triggers.token_threshold')
        default: Default value if key not found
        section: Optional section name

    Returns:
        Configuration value

    Examples:
        dsn = get_config_value('settings.json', 'sentry.dsn')
        threshold = get_config_value('auto-compact.json', 'triggers.token_threshold', default=150000)
    """
    config = load_config(config_name, section=section)

    # Navigate through nested keys
    keys = key_path.split('.')
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def load_command_restrictions_config() -> Dict[str, Any]:
    """
    Load command-restrictions.json configuration for command-restrictor.

    Returns:
        Command restrictions configuration
    """
    return load_config('command-restrictions.json', defaults={
        "enabled": True,
        "bash_restrictions": [],
        "tool_restrictions": [],
        "warning_patterns": [],
        "allowlist": [],
        "settings": {
            "warning_only_mode": False,
            "allow_user_override": False,
            "logging_enabled": True,
            "sentry_enabled": True,
            "use_settings_local": True
        }
    })


def load_settings_local() -> Dict[str, Any]:
    """
    Load settings.local.json configuration.

    Returns:
        Settings local configuration
    """
    return load_config('settings.local.json', defaults={
        "permissions": {
            "allow": [],
            "deny": [],
            "ask": []
        }
    })


def get_allowed_bash_patterns() -> List[str]:
    """
    Get allowed bash patterns from settings.local.json.

    Returns:
        List of allowed bash patterns

    Examples:
        Bash(cat:*) → cat*
        Bash(git status:*) → git status*
        Bash(python3:*) → python3*
    """
    settings_local = load_settings_local()
    permissions = settings_local.get('permissions', {})
    allow_list = permissions.get('allow', [])

    # Extract Bash(...) patterns
    bash_patterns = []
    for item in allow_list:
        if isinstance(item, str) and item.startswith('Bash('):
            # Extract pattern from Bash(pattern)
            pattern = item[5:-1]  # Remove 'Bash(' and ')'

            # Convert Claude Code permission format to bash command pattern
            # cat:* → cat* (matches "cat", "cat file.txt", etc.)
            if ':' in pattern:
                cmd, args = pattern.split(':', 1)
                if args == '*':
                    # cat:* → cat* (matches cat with any arguments)
                    bash_patterns.append(f"{cmd}*")
                else:
                    # Preserve other patterns as-is (e.g., curl:https://example.com)
                    bash_patterns.append(pattern)
            else:
                # No colon, use pattern as-is
                bash_patterns.append(pattern)

    return bash_patterns


def is_config_enabled(config_name: str, section: Optional[str] = None) -> bool:
    """
    Check if configuration is enabled.

    Args:
        config_name: Configuration file name
        section: Optional section name

    Returns:
        True if enabled, False otherwise
    """
    config = load_config(config_name, section=section)
    return config.get('enabled', True)
