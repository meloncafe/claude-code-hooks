#!/usr/bin/env python3
"""
Example Project - Git commit validation script.
Enforces commit message conventions and quality standards.
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from rich.console import Console

console = Console(stderr=True)

from common.sentry import init_sentry, capture_exception, add_breadcrumb, flush


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
        "commit_validation": {
            "enabled": True,
            "conventional_commits": True,
            "types": ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf", "ci", "build", "revert"],
            "scopes": ["auth", "session", "user", "token", "device", "email", "hooks", "schema", "service", "repository", "api", "test", "config", "deps", "core", "sdk"],
            "forbidden_patterns": ["TODO", "FIXME", "XXX", "HACK", "Co-Authored-By", "Co-authored-by"],
            "max_subject_length": 72,
            "max_body_line_length": 100,
            "imperative_verbs": ["add", "fix", "update", "remove", "refactor", "implement", "improve", "optimize", "enhance", "resolve"]
        },
        "forbidden_git_options": ["--no-verify", "--no-gpg-sign", "git -C", "gpgsign=false"]
    }


class CommitMessageValidator:
    """
    Example Project project commit message validator.
    """

    def __init__(self, message: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with message and configuration.

        Args:
            message: Commit message to validate
            config: Configuration from git-hooks.json
        """
        self.message = message
        self.lines = message.strip().split('\n')
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Load configuration from git-hooks.json or use defaults
        if config is None:
            config = load_git_hooks_config()

        validation_config = config.get('commit_validation', {})

        # Extract configuration values
        self.conventional_commits_enabled = validation_config.get('conventional_commits', True)
        self.block_co_authored = validation_config.get('block_co_authored', True)
        self.conventional_types = validation_config.get('types', [])
        self.project_scopes = validation_config.get('scopes', [])
        self.forbidden_patterns = validation_config.get('forbidden_patterns', [])
        self.max_subject_length = validation_config.get('max_subject_length', 72)
        self.max_body_line_length = validation_config.get('max_body_line_length', 100)
        self.imperative_verbs = validation_config.get('imperative_verbs', [])

        # Build forbidden pattern tuples with messages (excluding Co-Authored-By if block_co_authored is separate)
        self.forbidden_pattern_tuples = []
        for pattern in self.forbidden_patterns:
            # Skip Co-Authored-By patterns if block_co_authored setting exists separately
            if self.block_co_authored and pattern.lower() in ['co-authored-by', 'co-authored-by:']:
                continue
            self.forbidden_pattern_tuples.append(
                (r"\b" + re.escape(pattern) + r"\b", f"커밋 메시지에서 '{pattern}'를 제거하세요")
            )

        # Add Claude signature patterns
        self.forbidden_pattern_tuples.extend([
            (r"🤖 Generated with \[Claude Code\]", "Remove Claude signatures from commit messages."),
            (r"🤖 Generated with Claude", "Remove Claude signatures from commit messages."),
            (r"claude\.com|Claude Code", "Remove Claude-related content from the commit message."),
            (r"noreply@anthropic\.com", "Remove Anthropic emails from commit messages."),
        ])

        # Build past tense patterns from imperative verbs
        past_tense_forms = []
        verb_conjugations = {
            'add': 'added', 'fix': 'fixed', 'update': 'updated',
            'remove': 'removed', 'refactor': 'refactored',
            'implement': 'implemented', 'improve': 'improved',
            'optimize': 'optimized', 'enhance': 'enhanced',
            'resolve': 'resolved', 'delete': 'deleted',
            'change': 'changed', 'create': 'created', 'modify': 'modified'
        }

        for verb in self.imperative_verbs:
            past_form = verb_conjugations.get(verb, verb + 'ed')
            past_tense_forms.append(past_form)

        self.past_tense_pattern = re.compile(r'\b(' + '|'.join(past_tense_forms) + r')\b', re.IGNORECASE) if past_tense_forms else None

    def validate(self) -> Tuple[List[str], List[str]]:
        """Run Full Verification"""
        if not self.lines:
            self.errors.append("The commit message is empty.")
            return self.errors, self.warnings

        self._check_forbidden_patterns()
        self._validate_first_line()
        self._validate_body()

        return self.errors, self.warnings

    def _check_forbidden_patterns(self) -> None:
        """
        Check for forbidden patterns in commit message.
        """
        # Check Co-Authored-By separately if block_co_authored is enabled
        if self.block_co_authored:
            co_author_patterns = [
                r"Co-Authored-By:",
                r"Co-authored-by:",
                r"co-authored-by:"
            ]
            for pattern in co_author_patterns:
                if re.search(pattern, self.message, re.IGNORECASE):
                    self.errors.append(
                        "Co-authored commits are prohibited under project policy. "
                        "Please write it as a single commit."
                    )
                    break

        # Check other forbidden patterns
        for pattern, error_msg in self.forbidden_pattern_tuples:
            if re.search(pattern, self.message, re.IGNORECASE):
                self.errors.append(error_msg)

    def _validate_first_line(self) -> None:
        """
        Validate first line of commit message.
        """
        first_line = self.lines[0].strip()

        if len(first_line) < 10:
            self.errors.append(f"The commit message is too short (minimum 10 characters, currently {len(first_line)} characters)")

        if len(first_line) > self.max_subject_length:
            self.warnings.append(
                f"The first line must be {self.max_subject_length} characters or fewer (current: {len(first_line)} characters)."
            )

        if self.conventional_commits_enabled:
            self._validate_conventional_commit(first_line)

        self._check_imperative_mood(first_line)

    def _validate_conventional_commit(self, line: str) -> None:
        """
        Validate Conventional Commits format.
        """
        types_pattern = '|'.join(self.conventional_types) if self.conventional_types else 'feat|fix'
        pattern = f'^({types_pattern})' + r'(\([^)]+\))?: .+'

        if not re.match(pattern, line):
            self.warnings.append(
                "We recommend using the Conventional Commits format: "
                "type(scope)?: description\n"
                f"       Valid type: {', '.join(self.conventional_types)}"
            )
            return

        match = re.match(r'^([a-z]+)(\(([^)]+)\))?: (.+)', line)
        if match:
            commit_type, _, scope, description = match.groups()

            if self.conventional_types and commit_type not in self.conventional_types:
                self.warnings.append(
                    f"Unknown commit type '{commit_type}'. "
                    f"Valid type: {', '.join(self.conventional_types)}"
                )

            if scope and self.project_scopes and scope not in self.project_scopes:
                self.warnings.append(
                    f"Unknown scope '{scope}'. "
                    f"General Scope: {', '.join(self.project_scopes[:10])}"
                )

            if description and description[0].isupper():
                self.warnings.append(
                    "Conventional commit descriptions must start with a lowercase letter."
                )

    def _check_imperative_mood(self, line: str) -> None:
        """
        Check for imperative mood in commit message.
        """
        if self.past_tense_pattern and self.past_tense_pattern.search(line):
            self.warnings.append(
                "Use imperative verbs (e.g., 'Add feature' [GOOD], 'Added feature' [BAD])"
            )

    def _validate_body(self) -> None:
        """Body Verification"""
        if len(self.lines) <= 1:
            return

        if len(self.lines) > 1 and self.lines[1].strip() != "":
            self.errors.append("Add a blank line after the commit message summary.")


def extract_commit_message(command: str) -> Optional[str]:
    """Extracting Commit Messages from Git Commands (Combining All -m Flags)"""
    messages = re.findall(r'-m\s+["\'](.+?)["\']', command, re.DOTALL)
    if messages:
        return '\n\n'.join(messages)

    match = re.search(r'-m\s+(\S+)', command)
    if match:
        return match.group(1)

    return None


def is_git_commit_command(command: str) -> bool:
    """Verify if it is a Git commit command"""
    if not re.search(r'\bgit\b.*\bcommit\b', command):
        return False

    return True


def check_forbidden_git_options(command: str, config: Optional[Dict[str, Any]] = None) -> Tuple[List[str], List[str]]:
    """
    Check for forbidden Git options in command.

    Args:
        command: Git command to check
        config: Configuration from git-hooks.json

    Returns:
        Tuple of (error messages, git usage rules)
    """
    errors = []

    if config is None:
        config = load_git_hooks_config()

    validation_config = config.get('commit_validation', {})
    forbidden_git_options = validation_config.get('forbidden_git_options', [
        '--no-verify', '--no-gpg-sign', 'git -C', 'gpgsign=false'
    ])
    git_usage_rules = validation_config.get('git_usage_rules', [])

    # Build forbidden option patterns with messages
    forbidden_patterns = [
        (r'--no-verify', "git commit --no-verify is prohibited for security reasons."),
        (r'--no-gpg-sign', "Bypassing GPG signatures is prohibited."),
        (r'git\s+-C\s+', "The use of the `git -C` option is prohibited (bypassing the project directory)."),
        (r'-c\s+core\.hooksPath', "Changing the core.hooksPath setting is prohibited."),
        (r'-c\s+commit\.gpgsign=false', "Disabling GPG signatures is prohibited."),
    ]

    # Check only patterns that are in config
    for pattern, error_msg in forbidden_patterns:
        # Extract simple option name from pattern
        for forbidden_option in forbidden_git_options:
            if forbidden_option in pattern:
                if re.search(pattern, command):
                    errors.append(error_msg)
                break

    return errors, git_usage_rules


def create_hook_output(decision: str, reason: str, system_message: Optional[str] = None) -> Dict[str, Any]:
    """Claude Code hook output JSON generation"""
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
    sentry_enabled = init_sentry('validate-git-commit', additional_tags={'hook_type': 'pre_tool_use'})

    try:
        add_breadcrumb("Hook execution started", category="lifecycle")

        input_data = json.load(sys.stdin)
        add_breadcrumb("Input data loaded", category="input")
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON input: {e}"
        sys.stderr.write(f"\n❌ Error: {error_msg}\n")
        sys.stderr.flush()
        console.print(f"[red]Error: {error_msg}[/]")

        capture_exception(e, context={
            "hook": "validate-git-commit",
            "error_type": "json_decode_error"
        })

        flush()
        sys.exit(1)
    except Exception as e:
        error_msg = f"Unexpected error during input processing: {e}"
        sys.stderr.write(f"\n❌ Error: {error_msg}\n")
        sys.stderr.flush()
        console.print(f"[red]Error: {error_msg}[/]")

        capture_exception(e, context={
            "hook": "validate-git-commit",
            "error_type": "input_processing_error"
        })

        flush()
        sys.exit(1)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "PreToolUse":
        add_breadcrumb("Not PreToolUse event, skipping", category="filter")
        flush()
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        add_breadcrumb("Not Bash tool, skipping", category="filter")
        flush()
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")
    add_breadcrumb("Command extracted", category="command", data={"command_preview": command[:100]})

    if not is_git_commit_command(command):
        add_breadcrumb("Not git commit command, skipping", category="filter")
        flush()
        sys.exit(0)

    add_breadcrumb("Git commit command detected", category="validation")

    # Load configuration once for all validations
    config = load_git_hooks_config()
    add_breadcrumb("Config loaded", category="config")

    # Check if commit validation is enabled
    validation_config = config.get('commit_validation', {})
    if not validation_config.get('enabled', True):
        add_breadcrumb("Commit validation disabled in config", category="config")
        flush()
        sys.exit(0)

    forbidden_errors, git_usage_rules = check_forbidden_git_options(command, config)
    if forbidden_errors:
        add_breadcrumb("Forbidden git options detected", category="validation", level="error", data={"count": len(forbidden_errors)})

        reason = "[ERROR] A prohibited Git option has been detected.:\n\n"
        for error in forbidden_errors:
            reason += f"  • {error}\n"

        # Add git_usage_rules to the error message if available
        if git_usage_rules:
            reason += "\n[RULES] **Project Git Usage Rules:**\n"
            for rule in git_usage_rules:
                reason += f"  • {rule}\n"
        else:
            reason += "\n[TIP] Please comply with the project security policy."

        output = create_hook_output("deny", reason)
        print(json.dumps(output))

        flush()
        sys.exit(0)

    commit_message = extract_commit_message(command)
    add_breadcrumb("Commit message extracted", category="message", data={"length": len(commit_message) if commit_message else 0})

    if not commit_message:
        add_breadcrumb("No commit message (editor mode), skipping validation", category="filter")
        flush()
        sys.exit(0)

    add_breadcrumb("Starting commit message validation", category="validation")
    validator = CommitMessageValidator(commit_message, config)
    errors, warnings = validator.validate()

    add_breadcrumb("Validation completed", category="validation", data={
        "errors": len(errors),
        "warnings": len(warnings)
    })

    if errors:
        add_breadcrumb("Validation errors found, denying", category="validation", level="error", data={"error_count": len(errors)})

        reason = "[ERROR] Commit message validation failed!\n\n"
        reason += "**Error:**\n"
        for error in errors:
            reason += f"  • {error}\n"

        if warnings:
            reason += "\n**Warning:**\n"
            for warning in warnings:
                reason += f"  [WARNING] {warning}\n"

        reason += "\n[TIP] Please modify the commit message and try again."

        output = create_hook_output("deny", reason)
        print(json.dumps(output))

        flush()
        sys.exit(0)

    if warnings:
        add_breadcrumb("Validation warnings found, denying", category="validation", level="warning", data={"warning_count": len(warnings)})

        reason = "[WARNING] Commit Message Validation Warning!\n\n"
        reason += "**Warning:**\n"
        for warning in warnings:
            reason += f"  • {warning}\n"
        reason += "\n[TIP] Improve your commit message and try again."

        output = create_hook_output("deny", reason)
        print(json.dumps(output))

        flush()
        sys.exit(0)

    add_breadcrumb("All validations passed", category="validation")
    flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
