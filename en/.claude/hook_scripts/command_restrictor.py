#!/usr/bin/env python3
"""
Claude Code Hook: Command Restrictor

Hook Event: PreToolUse
"""
import json
import re
import sys
import traceback
from fnmatch import fnmatch
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from rich.console import Console

console = Console(stderr=True)

from common.config import load_command_restrictions_config, get_allowed_bash_patterns
from common.logger import HookLogger
from common.sentry import init_sentry, capture_exception, add_breadcrumb, flush
from common.project import ensure_project_root


class CommandRestrictor:
    """
    Command and tool usage restrictor with alternative suggestions.
    """

    def __init__(self, config: Dict[str, Any], logger: HookLogger):
        """
        Initialize restrictor with configuration.

        Args:
            config: Configuration from command-restrictions.json
            logger: Hook logger instance
        """
        self.config = config
        self.logger = logger
        self.enabled = config.get('enabled', True)

        # Settings
        settings = config.get('settings', {})
        self.warning_only_mode = settings.get('warning_only_mode', False)
        self.allow_user_override = settings.get('allow_user_override', False)

        # Load restrictions
        self.bash_restrictions = [
            r for r in config.get('bash_restrictions', [])
            if r.get('enabled', True)
        ]
        self.tool_restrictions = [
            r for r in config.get('tool_restrictions', [])
            if r.get('enabled', True)
        ]
        self.warning_patterns = [
            r for r in config.get('warning_patterns', [])
            if r.get('enabled', True)
        ]
        self.allowlist = config.get('allowlist', [])

        # Load settings.local.json patterns if enabled
        self.use_settings_local = settings.get('use_settings_local', True)
        self.settings_local_patterns: List[str] = []
        if self.use_settings_local:
            try:
                self.settings_local_patterns = get_allowed_bash_patterns()
                self.logger.log_info(
                    "Loaded settings.local.json patterns",
                    count=len(self.settings_local_patterns),
                    sample_patterns=self.settings_local_patterns[:10]  # Show first 10
                )
            except Exception as e:
                self.logger.log_error(
                    "Failed to load settings.local.json",
                    error=str(e)
                )
                capture_exception(e)

        self.logger.log_info(
            "CommandRestrictor initialized",
            restrictions_count=len(self.bash_restrictions),
            tool_restrictions_count=len(self.tool_restrictions),
            warning_patterns_count=len(self.warning_patterns),
            allowlist_count=len(self.allowlist),
            settings_local_count=len(self.settings_local_patterns)
        )

    def _match_pattern(self, text: str, pattern_config: Dict[str, str]) -> bool:
        """
        Match text against pattern (regex or wildcard).

        Args:
            text: Text to match
            pattern_config: Pattern configuration with 'pattern' and 'type'

        Returns:
            True if matched, False otherwise
        """
        pattern = pattern_config.get('pattern', '')
        pattern_type = pattern_config.get('type', 'regex')

        try:
            if pattern_type == 'wildcard':
                # Wildcard matching (glob style)
                first_line = text.split('\n')[0] if '\n' in text else text
                return fnmatch(first_line, pattern)
            else:
                # Regex matching (default)
                return bool(re.search(pattern, text))
        except (re.error, Exception) as e:
            self.logger.log_error(
                "Pattern matching error",
                pattern=pattern,
                pattern_type=pattern_type,
                error=str(e)
            )
            capture_exception(e, context={
                "pattern": pattern,
                "pattern_type": pattern_type
            })
            return False

    def is_settings_local_allowed(self, command: str) -> bool:
        """
        Check if command matches settings.local.json allow patterns.

        Args:
            command: Command to check

        Returns:
            True if allowed by settings.local, False otherwise
        """
        if not self.use_settings_local:
            return False

        for pattern in self.settings_local_patterns:
            # settings.local.json patterns are wildcard style
            if fnmatch(command, pattern):
                self.logger.log_info(
                    "Command matched settings.local.json",
                    pattern=pattern
                )
                add_breadcrumb(
                    "Command matched settings.local.json",
                    category="settings_local",
                    data={"pattern": pattern}
                )
                return True
        return False

    def is_allowed(self, command: str) -> bool:
        """
        Check if command matches allowlist.

        Args:
            command: Command to check

        Returns:
            True if allowed, False otherwise
        """
        for allow_item in self.allowlist:
            pattern_config = {
                'pattern': allow_item.get('pattern', ''),
                'type': allow_item.get('type', 'regex')
            }

            if self._match_pattern(command, pattern_config):
                reason = allow_item.get('reason', '')

                comment = allow_item.get('comment', '')
                if comment:
                    console.print(f"[dim]# {comment}[/]")

                self.logger.log_info(
                    "Command matched allowlist",
                    pattern=pattern_config['pattern'],
                    type=pattern_config['type'],
                    reason=reason
                )
                add_breadcrumb(
                    "Command matched allowlist",
                    category="allowlist",
                    data={"pattern": pattern_config['pattern'], "reason": reason}
                )
                return True
        return False

    def check_bash_command(self, command: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Check bash command against restrictions.

        Args:
            command: Bash command to check

        Returns:
            Tuple of (restriction_match, warning_match) if found, (None, None) otherwise
        """
        # Check settings.local.json first (highest priority)
        if self.is_settings_local_allowed(command):
            return None, None

        # Check critical restrictions
        for restriction in self.bash_restrictions:
            patterns = restriction.get('patterns', [])
            for pattern_config in patterns:
                if self._match_pattern(command, pattern_config):
                    self.logger.log_info(
                        "Bash restriction matched",
                        name=restriction.get('name', ''),
                        pattern=pattern_config.get('pattern', ''),
                        type=pattern_config.get('type', 'regex'),
                        severity=restriction.get('severity', ''),
                        command_preview=command[:100]
                    )
                    add_breadcrumb(
                        "Bash restriction matched",
                        category="restriction",
                        data={
                            "name": restriction.get('name', ''),
                            "pattern": pattern_config.get('pattern', ''),
                            "severity": restriction.get('severity', '')
                        }
                    )
                    return restriction, None

        # Check warning patterns (before allowlist for important confirmations)
        for warning in self.warning_patterns:
            patterns = warning.get('patterns', [])
            for pattern_config in patterns:
                if self._match_pattern(command, pattern_config):
                    self.logger.log_info(
                        "Warning pattern matched",
                        name=warning.get('name', ''),
                        pattern=pattern_config.get('pattern', ''),
                        type=pattern_config.get('type', 'regex'),
                        command_preview=command[:100]
                    )
                    add_breadcrumb(
                        "Warning pattern matched",
                        category="warning",
                        data={
                            "name": warning.get('name', ''),
                            "pattern": pattern_config.get('pattern', '')
                        }
                    )
                    return None, warning

        # Check if command is in allowlist (after warnings)
        if self.is_allowed(command):
            return None, None

        return None, None

    def check_tool_usage(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if tool usage is restricted.

        Args:
            tool_name: Name of the tool

        Returns:
            Restriction config if restricted, None otherwise
        """
        for restriction in self.tool_restrictions:
            if restriction.get('tool_name', '') == tool_name:
                self.logger.log_info(
                    "Tool restriction matched",
                    tool=tool_name,
                    severity=restriction.get('severity', '')
                )
                add_breadcrumb(
                    "Tool restriction matched",
                    category="restriction",
                    data={
                        "tool": tool_name,
                        "severity": restriction.get('severity', '')
                    }
                )
                return restriction
        return None

    def format_restriction_message(
        self,
        restriction: Dict[str, Any],
        is_warning: bool = False
    ) -> str:
        """
        Format restriction message with alternatives.

        Args:
            restriction: Restriction configuration
            is_warning: Whether this is a warning (not blocking)

        Returns:
            Formatted message
        """
        severity = restriction.get('severity', 'medium')
        severity_emoji = {
            'critical': '[CRITICAL]',
            'high': '[ERROR]',
            'medium': '[WARNING]',
            'low': '[INFO]'
        }.get(severity, '[WARNING]')

        if is_warning:
            severity_emoji = '[WARNING]'
            header = f"{severity_emoji} 경고: {restriction.get('name', '명령어 사용')}"
        else:
            header = f"{severity_emoji} 차단됨: {restriction.get('name', '명령어 사용')}"

        message = f"{header}\n\n"
        message += f"**사유:**\n{restriction.get('reason', '이 명령어는 제한되어 있습니다')}\n\n"

        alternatives = restriction.get('alternatives', [])
        if alternatives:
            message += "**권장 대안:**\n"
            for alt in alternatives:
                message += f"  • {alt}\n"

        if is_warning:
            message += "\n[TIP] 위 사항을 검토하고 진행하세요."
        else:
            message += "\n[TIP] 위 대안 중 하나를 사용하여 다시 시도하세요."

        return message


def create_hook_output(
    decision: str,
    reason: str,
    system_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create Claude Code hook output JSON.

    Args:
        decision: Permission decision (allow, deny, ask)
        reason: Reason for decision
        system_message: Optional system message

    Returns:
        Hook output dictionary
    """
    output: Dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }

    if system_message:
        output["systemMessage"] = system_message

    return output


def main():
    """
    Claude Code Hook main logic.
    """
    logger = HookLogger('command-restrictor')
    logger.log_start()

    init_sentry(
        'command-restrictor',
        additional_tags={'hook_type': 'pre_tool_use'}
    )

    # Ensure we're at project root
    if not ensure_project_root():
        console.print("[yellow]Warning: Could not find project root (.claude directory)[/]")
        logger.log_warning("Project root not found")

    try:
        add_breadcrumb("Hook execution started", category="lifecycle")

        try:
            input_data = json.load(sys.stdin)
            add_breadcrumb("Input data loaded", category="input")
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON input: {e}"
            console.print(f"[red bold]Error: {error_msg}[/]")
            logger.log_error("JSON decode error", error=str(e))
            capture_exception(e, context={
                "hook": "command-restrictor",
                "error_type": "json_decode_error"
            })
            logger.log_end(success=False)
            flush()
            sys.exit(1)

        hook_event = input_data.get("hook_event_name", "")
        if hook_event != "PreToolUse":
            add_breadcrumb("Not PreToolUse event, skipping", category="filter")
            logger.log_end(success=True, skipped=True, reason="not_pretooluse")
            flush()
            sys.exit(0)

        config = load_command_restrictions_config()
        restrictor = CommandRestrictor(config, logger)

        if not restrictor.enabled:
            add_breadcrumb("Command restrictor disabled", category="config")
            logger.log_end(success=True, skipped=True, reason="disabled")
            flush()
            sys.exit(0)

        add_breadcrumb("Restrictor initialized", category="config")

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        add_breadcrumb(
            "Tool detected",
            category="tool",
            data={"tool_name": tool_name}
        )

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            logger.log_info(
                "Checking Bash command",
                command_preview=command[:100]
            )
            add_breadcrumb(
                "Bash command detected",
                category="command",
                data={"command_preview": command[:100]}
            )

            restriction, warning = restrictor.check_bash_command(command)

            if restriction:
                message = restrictor.format_restriction_message(restriction, is_warning=False)
                decision = "ask" if restrictor.allow_user_override else "deny"

                logger.log_info(
                    "Command blocked",
                    restriction=restriction.get('name', ''),
                    decision=decision,
                    severity=restriction.get('severity', ''),
                    command_preview=command[:100]
                )

                output = create_hook_output(decision, message)
                print(json.dumps(output))

                add_breadcrumb(
                    "Command blocked",
                    category="restriction",
                    level="warning",
                    data={"restriction": restriction.get('name', '')}
                )
                logger.log_end(success=True, action="blocked")
                flush()
                sys.exit(0)

            if warning:
                message = restrictor.format_restriction_message(warning, is_warning=True)

                if restrictor.warning_only_mode:
                    decision = "allow"
                else:
                    decision = "ask"

                logger.log_info(
                    "Warning issued",
                    warning=warning.get('name', ''),
                    decision=decision,
                    command_preview=command[:100]
                )

                output = create_hook_output(decision, message)
                print(json.dumps(output))

                add_breadcrumb(
                    "Warning issued",
                    category="warning",
                    data={"warning": warning.get('name', '')}
                )
                logger.log_end(success=True, action="warned")
                flush()
                sys.exit(0)

        restriction = restrictor.check_tool_usage(tool_name)
        if restriction:
            message = restrictor.format_restriction_message(restriction, is_warning=False)
            decision = "ask" if restrictor.allow_user_override else "deny"

            logger.log_info(
                "Tool usage blocked",
                tool=tool_name,
                decision=decision,
                severity=restriction.get('severity', '')
            )

            output = create_hook_output(decision, message)
            print(json.dumps(output))

            add_breadcrumb(
                "Tool usage blocked",
                category="restriction",
                level="warning",
                data={"tool": tool_name}
            )
            logger.log_end(success=True, action="tool_blocked")
            flush()
            sys.exit(0)

        add_breadcrumb("All checks passed", category="validation")
        logger.log_end(success=True, action="allowed")

        output = create_hook_output("allow", "Command execution is permitted.")
        print(json.dumps(output))

        flush()
        sys.exit(0)

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        console.print(f"[red bold]Error: {error_msg}[/]")
        import traceback
        console.print(traceback.format_exc(), style="red dim")

        logger.log_error("Unexpected error", error=str(e), traceback=traceback.format_exc())

        capture_exception(e, context={
            "hook": "command-restrictor",
            "error_type": "unexpected_error"
        })

        logger.log_end(success=False)
        flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
