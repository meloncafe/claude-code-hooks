#!/usr/bin/env python3
"""
Example Project - Code pattern enforcement script.
Enforces coding patterns and best practices.
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from rich.console import Console

console = Console(stderr=True)

from common.sentry import init_sentry, capture_exception, add_breadcrumb, flush


def load_pattern_config() -> Dict[str, Any]:
    """
    Load code-quality.json and command-restrictions.json configuration files.
    """
    candidates = [
        Path.cwd() / ".claude" / "config",
        Path.home() / ".claude" / "config",
    ]

    config = {
        "forbidden_patterns": {},
        "enabled": True
    }

    for base_path in candidates:
        code_quality_path = base_path / "code-quality.json"
        if code_quality_path.exists():
            try:
                with open(code_quality_path, 'r', encoding='utf-8') as f:
                    config["code_quality"] = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

    # Default forbidden patterns
    config["forbidden_patterns"] = {
        "getattr": {
            "pattern": r"\bgetattr\s*\(",
            "message": "The use of `getattr()` is prohibited. Use explicit attribute access instead.",
            "alternatives": [
                "Explicit property access using try-except:",
                "  try:",
                "      value = obj.attribute",
                "  except AttributeError:",
                "      value = None",
                "",
                "or isinstance check:",
                "  if isinstance(obj, ExpectedClass):",
                "      value = obj.attribute"
            ],
            "severity": "high",
            "reference": ".claude/skills/example-backend/SKILL.md - Dynamic property access prohibited"
        },
        "setattr": {
            "pattern": r"\bsetattr\s*\(",
            "message": "The use of `setattr()` is prohibited. Use explicit attribute assignment instead.",
            "alternatives": [
                "Explicit property assignment:",
                "  obj.attribute = value",
                "",
                "Using Pydantic Models:",
                "  from pydantic import BaseModel",
                "  class MyModel(BaseModel):",
                "      attribute: str"
            ],
            "severity": "high",
            "reference": ".claude/skills/example-backend/SKILL.md - Dynamic property access prohibited"
        },
        "hasattr": {
            "pattern": r"\bhasattr\s*\(",
            "message": "The use of `hasattr()` is prohibited. Use `isinstance` or `try-except` instead.",
            "alternatives": [
                "isinstance check:",
                "  if isinstance(obj, ExpectedClass):",
                "      # obj.attribute is available",
                "",
                "try-except:",
                "  try:",
                "      value = obj.attribute",
                "  except AttributeError:",
                "      # No Attributes Processing"
            ],
            "severity": "high",
            "reference": ".claude/skills/example-backend/SKILL.md - Dynamic property access prohibited"
        },
        "delattr": {
            "pattern": r"\bdelattr\s*\(",
            "message": "The use of delattr() is prohibited. Use del obj.attribute instead.",
            "alternatives": [
                "Explicit deletion:",
                "  del obj.attribute"
            ],
            "severity": "high",
            "reference": ".claude/skills/example-backend/SKILL.md - Dynamic property access prohibited"
        }
    }

    return config


class CodePatternValidator:
    """
    Example Project project code pattern validator.
    """

    def __init__(self, file_path: str, content: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with file path, content and configuration.

        Args:
            file_path: Path to the file being edited
            content: File content to validate
            config: Configuration from code-quality.json
        """
        self.file_path = file_path
        self.content = content
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Load configuration
        if config is None:
            config = load_pattern_config()

        self.config = config
        self.forbidden_patterns = config.get("forbidden_patterns", {})

    def should_skip_validation(self) -> bool:
        """
        Check if file should skip validation.
        """
        # Skip test files
        test_patterns = [
            r"test_.*\.py$",
            r".*_test\.py$",
            r"/tests?/",
            r"conftest\.py$",
            r"\.test\.",
            r"\.spec\.",
        ]

        for pattern in test_patterns:
            if re.search(pattern, self.file_path):
                return True

        # Skip non-Python files for code pattern checks
        if not self.file_path.endswith('.py'):
            return True

        return False

    def validate(self) -> Tuple[List[str], List[str]]:
        """
        Run full validation.
        """
        if self.should_skip_validation():
            return self.errors, self.warnings

        # Check forbidden patterns
        self._check_forbidden_patterns()

        # Check Repository/Service pattern (only for Service files)
        if 'service' in self.file_path.lower() and 'class' in self.content.lower():
            self._check_repository_pattern()

        return self.errors, self.warnings

    def _check_forbidden_patterns(self) -> None:
        """
        Check for forbidden code patterns.
        """
        lines = self.content.split('\n')

        for pattern_name, pattern_info in self.forbidden_patterns.items():
            pattern = pattern_info["pattern"]
            matches = []

            # Find all matches with line numbers
            for line_num, line in enumerate(lines, 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue

                if re.search(pattern, line):
                    matches.append((line_num, line.strip()))

            if matches:
                error_msg = f"[{pattern_name.upper()}] {pattern_info['message']}\n"
                error_msg += f"\nDiscovered location:\n"
                for line_num, line_content in matches:
                    error_msg += f"  {self.file_path}:{line_num}\n"
                    error_msg += f"    {line_content[:80]}\n"

                error_msg += f"\nAlternative:\n"
                for alt in pattern_info.get('alternatives', []):
                    error_msg += f"  {alt}\n"

                error_msg += f"\nReference: {pattern_info.get('reference', 'Backend Skill Document')}"

                self.errors.append(error_msg)

    def _check_repository_pattern(self) -> None:
        """
        Check if Service classes use Repository pattern.

        Note: This is a soft check - warns but doesn't block.
        """
        # Find Service class definitions
        service_class_pattern = r"class\s+\w+Service\s*(?:\(|:)"
        service_classes = re.findall(service_class_pattern, self.content)

        if not service_classes:
            return

        # Check if Repository is imported or used
        has_repository_import = bool(re.search(r"from\s+.*\s+import\s+.*Repository", self.content))
        has_repository_usage = bool(re.search(r"self\.\w*repo(?:sitory)?", self.content, re.IGNORECASE))

        # Only warn if it looks like a Service that might need Repository
        # (has database-like method names but no Repository usage)
        db_method_patterns = [
            r"def\s+(?:get|create|update|delete|save|find|list)_",
            r"session\.",
            r"await\s+.*\.execute",
        ]

        has_db_methods = any(re.search(pattern, self.content) for pattern in db_method_patterns)

        if has_db_methods and not (has_repository_import or has_repository_usage):
            self.warnings.append(
                "[PATTERN] Database access was detected in the Service class.\n"
                "\n"
                "Recommendation: Use the Repository pattern.\n"
                "  - Repository: Data Access Logic\n"
                "  - Service: Business Logic\n"
                "\n"
                "Reference: .claude/skills/example-backend/SKILL.md - Repository/Service Separation"
            )


def create_hook_output(decision: str, reason: str, system_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create Claude Code hook output JSON.
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


def extract_file_content(tool_input: Dict[str, Any], tool_name: str) -> Optional[Tuple[str, str]]:
    """
    Extract file path and content from tool input.

    Returns:
        Tuple of (file_path, content) or None
    """
    if tool_name == "Edit":
        file_path = tool_input.get("file_path")
        new_string = tool_input.get("new_string", "")
        if file_path and new_string:
            return file_path, new_string

    elif tool_name == "Write":
        file_path = tool_input.get("file_path")
        content = tool_input.get("content", "")
        if file_path and content:
            return file_path, content

    return None


def main():
    """
    Claude Code Hook main logic.
    """
    sentry_enabled = init_sentry('pattern-enforcer', additional_tags={'hook_type': 'pre_tool_use'})

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
            "hook": "pattern-enforcer",
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
            "hook": "pattern-enforcer",
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
    if tool_name not in ["Edit", "Write"]:
        add_breadcrumb("Not Edit/Write tool, skipping", category="filter")
        flush()
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    file_info = extract_file_content(tool_input, tool_name)

    if not file_info:
        add_breadcrumb("No file content to validate, skipping", category="filter")
        flush()
        sys.exit(0)

    file_path, content = file_info
    add_breadcrumb("File content extracted", category="content", data={
        "file_path": file_path,
        "content_length": len(content)
    })

    # Load configuration
    config = load_pattern_config()
    add_breadcrumb("Config loaded", category="config")

    # Check if validation is enabled
    if not config.get('enabled', True):
        add_breadcrumb("Pattern validation disabled in config", category="config")
        flush()
        sys.exit(0)

    add_breadcrumb("Starting pattern validation", category="validation")
    validator = CodePatternValidator(file_path, content, config)
    errors, warnings = validator.validate()

    add_breadcrumb("Validation completed", category="validation", data={
        "errors": len(errors),
        "warnings": len(warnings)
    })

    if errors:
        add_breadcrumb("Validation errors found, denying", category="validation", level="error", data={"error_count": len(errors)})

        reason = "❌ [Code Pattern Verification Failed]\n\n"
        reason += "**Error:**\n"
        for error in errors:
            reason += f"{error}\n\n"

        if warnings:
            reason += "**Warning:**\n"
            for warning in warnings:
                reason += f"{warning}\n\n"

        reason += "\n💡 Refer to the Backend Skills documentation.:\n"
        reason += "  .claude/skills/example-backend/SKILL.md"

        output = create_hook_output("deny", reason)
        print(json.dumps(output))

        flush()
        sys.exit(0)

    if warnings:
        add_breadcrumb("Validation warnings found, allowing with notice", category="validation", level="warning", data={"warning_count": len(warnings)})

        reason = "⚠️ [Code Pattern Warning]\n\n"
        for warning in warnings:
            reason += f"{warning}\n\n"

        flush()
        sys.exit(0)

    add_breadcrumb("All validations passed", category="validation")
    flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
