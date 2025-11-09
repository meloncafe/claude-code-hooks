#!/usr/bin/env python3
"""
Sentry Integration Utilities
"""
import sys
from typing import Dict, Any, Optional, Literal

import sentry_sdk
from rich.console import Console
from sentry_sdk.integrations.argv import ArgvIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration
from sentry_sdk.types import Event, Hint

from .config import load_settings

console = Console(stderr=True)

_sentry_initialized = False


def filter_sensitive_data(event: Event, hint: Hint) -> Optional[Event]:
    """
    Filter sensitive data from Sentry events before sending.

    Args:
        event: Sentry event object
        hint: Additional context about the event

    Returns:
        Filtered event or None to drop the event
    """
    # Filter environment variables
    if 'contexts' in event and 'runtime' in event['contexts']:
        runtime = event['contexts']['runtime']
        if 'env' in runtime:
            # Remove potentially sensitive env vars
            sensitive_keys = ['KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'API', 'DSN']
            runtime['env'] = {
                k: '***FILTERED***' if any(s in k.upper() for s in sensitive_keys) else v
                for k, v in runtime['env'].items()
            }

    # Filter request data if present
    if 'request' in event:
        request = event['request']
        if 'headers' in request:
            # Remove authorization headers
            sensitive_headers = ['Authorization', 'Cookie', 'X-Api-Key']
            for header in sensitive_headers:
                if header in request['headers']:
                    request['headers'][header] = '***FILTERED***'

    # Filter extra data
    if 'extra' in event:
        extra = event['extra']
        sensitive_keys = ['password', 'token', 'api_key', 'secret', 'dsn']
        for key in list(extra.keys()):
            if any(s in key.lower() for s in sensitive_keys):
                extra[key] = '***FILTERED***'

    return event


def init_sentry(script_name: str, additional_tags: Optional[Dict[str, str]] = None) -> bool:
    """
    Initialize Sentry SDK for error tracking.

    Args:
        script_name: Name of the hook script (e.g., 'auto-compact')
        additional_tags: Additional tags to add to all events

    Returns:
        True if Sentry was initialized, False otherwise
    """
    global _sentry_initialized

    # Return early if already initialized
    if _sentry_initialized:
        return True

    # Load settings
    settings = load_settings()
    sentry_config = settings.get('sentry', {})

    # Check if Sentry is enabled
    if not sentry_config.get('enabled', False):
        return False

    # Get DSN
    dsn = sentry_config.get('dsn')
    if not dsn:
        return False

    try:
        # Prepare tags
        tags = {
            'script': script_name,
            'project': settings.get('project', 'example_project'),
            'component': 'claude_code_hooks',
        }

        # Add configured tags
        configured_tags = sentry_config.get('tags', {})
        tags.update(configured_tags)

        # Add additional tags
        if additional_tags:
            tags.update(additional_tags)

        # Prepare integrations
        integrations = []
        integrations_config = sentry_config.get('integrations', {})

        if integrations_config.get('logging', True):
            integrations.append(LoggingIntegration(
                level=None,  # Capture all levels
                event_level=None  # Send all as breadcrumbs
            ))

        if integrations_config.get('threading', True):
            integrations.append(ThreadingIntegration(propagate_hub=True))

        if integrations_config.get('modules', True):
            integrations.append(ModulesIntegration())

        if integrations_config.get('argv', True):
            integrations.append(ArgvIntegration())

        # Map before_send configuration to function
        before_send_func = None
        before_send_config = sentry_config.get('before_send', 'filter_sensitive_data')
        if before_send_config == 'filter_sensitive_data':
            before_send_func = filter_sensitive_data
        # If 'none' or empty string, before_send_func stays None

        # Initialize Sentry
        sentry_sdk.init(
            dsn=dsn,
            environment=sentry_config.get('environment', 'development'),
            traces_sample_rate=sentry_config.get('traces_sample_rate', 1.0),
            profiles_sample_rate=sentry_config.get('profiles_sample_rate', 1.0),
            send_default_pii=sentry_config.get('send_default_pii', False),
            attach_stacktrace=sentry_config.get('attach_stacktrace', True),
            max_breadcrumbs=sentry_config.get('max_breadcrumbs', 50),
            before_send=before_send_func,
            integrations=integrations,
        )

        # Set tags
        for key, value in tags.items():
            sentry_sdk.set_tag(key, value)

        # Set context
        sentry_sdk.set_context('hook', {
            'script_name': script_name,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'platform': sys.platform,
        })

        _sentry_initialized = True
        return True

    except Exception as e:
        # Sentry initialization failed, but don't crash the hook
        console.print(f"[yellow]WARNING: Sentry initialization failed: {e}[/]")
        return False


def capture_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
) -> Optional[str]:
    """
    Capture an exception and send to Sentry.

    Args:
        exception: The exception to capture
        context: Additional context data
        level: Severity level (error, warning, info)

    Returns:
        Event ID if sent, None otherwise
    """
    if not _sentry_initialized:
        return None

    try:
        # Add context if provided
        if context:
            sentry_sdk.set_context('additional', context)

        # Capture exception
        event_id = sentry_sdk.capture_exception(exception)
        return event_id

    except Exception:
        # Failed to send to Sentry, but don't crash
        return None


def capture_message(
    message: str,
    level: Literal["fatal", "critical", "error", "warning", "info", "debug"] = "info",
    context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Severity level (fatal, critical, error, warning, info, debug)
        context: Additional context data

    Returns:
        Event ID if sent, None otherwise
    """
    if not _sentry_initialized:
        return None

    try:
        # Add context if provided
        if context:
            sentry_sdk.set_context('additional', context)

        # Capture message
        event_id = sentry_sdk.capture_message(message, level=level)
        return event_id

    except Exception:
        # Failed to send to Sentry, but don't crash
        return None


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: Literal["fatal", "critical", "error", "warning", "info", "debug"] = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a breadcrumb to the current scope.

    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Severity level (fatal, critical, error, warning, info, debug)
        data: Additional data
    """
    if not _sentry_initialized:
        return

    try:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
    except Exception:
        # Failed to add breadcrumb, but don't crash
        pass


def flush(timeout: float = 2.0) -> None:
    """
    Flush pending events to Sentry.

    Args:
        timeout: Maximum time to wait for flush (seconds)
    """
    if not _sentry_initialized:
        return

    try:
        sentry_sdk.flush(timeout=timeout)
    except Exception:
        pass
