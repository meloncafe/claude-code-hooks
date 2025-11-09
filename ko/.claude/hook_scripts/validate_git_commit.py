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
    Example Project 프로젝트 커밋 메시지 검증기.
    """

    def __init__(self, message: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize validator with message and configuration.
        메시지와 설정으로 검증기 초기화.

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
            (r"🤖 Generated with \[Claude Code\]", "커밋 메시지에서 Claude 서명을 제거하세요"),
            (r"🤖 Generated with Claude", "커밋 메시지에서 Claude 서명을 제거하세요"),
            (r"claude\.com|Claude Code", "커밋 메시지에서 Claude 관련 내용을 제거하세요"),
            (r"noreply@anthropic\.com", "커밋 메시지에서 Anthropic 이메일을 제거하세요"),
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
        """전체 검증 실행"""
        if not self.lines:
            self.errors.append("커밋 메시지가 비어있습니다")
            return self.errors, self.warnings

        self._check_forbidden_patterns()
        self._validate_first_line()
        self._validate_body()

        return self.errors, self.warnings

    def _check_forbidden_patterns(self) -> None:
        """
        Check for forbidden patterns in commit message.
        커밋 메시지의 금지된 패턴 확인.
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
                        "Co-authored 커밋은 프로젝트 정책상 금지되어 있습니다. "
                        "단독 커밋으로 작성해 주세요."
                    )
                    break

        # Check other forbidden patterns
        for pattern, error_msg in self.forbidden_pattern_tuples:
            if re.search(pattern, self.message, re.IGNORECASE):
                self.errors.append(error_msg)

    def _validate_first_line(self) -> None:
        """
        Validate first line of commit message.
        커밋 메시지 첫 줄 검증.
        """
        first_line = self.lines[0].strip()

        # 최소 길이 체크
        if len(first_line) < 10:
            self.errors.append(f"커밋 메시지가 너무 짧습니다 (최소 10자, 현재 {len(first_line)}자)")

        # 최대 길이 경고
        if len(first_line) > self.max_subject_length:
            self.warnings.append(
                f"첫 줄은 {self.max_subject_length}자 이하여야 합니다 (현재: {len(first_line)}자)"
            )

        # Conventional Commits 검증 (설정에서 활성화된 경우만)
        if self.conventional_commits_enabled:
            self._validate_conventional_commit(first_line)

        # 명령형 동사 체크
        self._check_imperative_mood(first_line)

    def _validate_conventional_commit(self, line: str) -> None:
        """
        Validate Conventional Commits format.
        Conventional Commits 형식 검증.
        """
        # 기본 패턴: type(scope)?: description
        types_pattern = '|'.join(self.conventional_types) if self.conventional_types else 'feat|fix'
        pattern = f'^({types_pattern})' + r'(\([^)]+\))?: .+'

        if not re.match(pattern, line):
            self.warnings.append(
                "Conventional Commits 형식 사용을 권장합니다: "
                "type(scope)?: description\n"
                f"       유효한 타입: {', '.join(self.conventional_types)}"
            )
            return

        # Conventional Commits 형식일 경우 추가 검증
        match = re.match(r'^([a-z]+)(\(([^)]+)\))?: (.+)', line)
        if match:
            commit_type, _, scope, description = match.groups()

            # 타입 검증
            if self.conventional_types and commit_type not in self.conventional_types:
                self.warnings.append(
                    f"알 수 없는 커밋 타입 '{commit_type}'. "
                    f"유효한 타입: {', '.join(self.conventional_types)}"
                )

            # 스코프 검증 (선택적)
            if scope and self.project_scopes and scope not in self.project_scopes:
                self.warnings.append(
                    f"알 수 없는 스코프 '{scope}'. "
                    f"일반적인 스코프: {', '.join(self.project_scopes[:10])}"
                )

            # 설명 첫 글자는 소문자
            if description and description[0].isupper():
                self.warnings.append(
                    "Conventional commit 설명은 소문자로 시작해야 합니다"
                )

    def _check_imperative_mood(self, line: str) -> None:
        """
        Check for imperative mood in commit message.
        커밋 메시지의 명령형 동사 사용 체크.
        """
        if self.past_tense_pattern and self.past_tense_pattern.search(line):
            self.warnings.append(
                "명령형 동사를 사용하세요 (예: 'Add feature' [GOOD], 'Added feature' [BAD])"
            )

    def _validate_body(self) -> None:
        """본문 검증"""
        if len(self.lines) <= 1:
            return

        # 첫 줄 다음에 빈 줄 확인
        if len(self.lines) > 1 and self.lines[1].strip() != "":
            self.errors.append("커밋 메시지 요약 다음에 빈 줄을 추가하세요")


def extract_commit_message(command: str) -> Optional[str]:
    """Git 명령어에서 커밋 메시지 추출 (모든 -m 플래그 통합)"""
    # 모든 -m "message" 패턴 추출 (멀티라인 지원)
    messages = re.findall(r'-m\s+["\'](.+?)["\']', command, re.DOTALL)
    if messages:
        # 모든 메시지를 두 줄바꿈으로 연결 (git commit -m 여러 개 사용 시와 동일)
        return '\n\n'.join(messages)

    # -m message (따옴표 없음, 공백 없는 경우)
    match = re.search(r'-m\s+(\S+)', command)
    if match:
        return match.group(1)

    return None


def is_git_commit_command(command: str) -> bool:
    """Git commit 명령어인지 확인"""
    # git commit 패턴 확인 (git -C, git --no-verify 등 포함)
    if not re.search(r'\bgit\b.*\bcommit\b', command):
        return False

    return True


def check_forbidden_git_options(command: str, config: Optional[Dict[str, Any]] = None) -> Tuple[List[str], List[str]]:
    """
    Check for forbidden Git options in command.
    명령어에서 금지된 Git 옵션 확인.

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
        (r'--no-verify', "git commit --no-verify는 보안상 금지되어 있습니다"),
        (r'--no-gpg-sign', "GPG 서명을 우회하는 것은 금지되어 있습니다"),
        (r'git\s+-C\s+', "git -C 옵션 사용은 금지되어 있습니다 (프로젝트 디렉토리 우회)"),
        (r'-c\s+core\.hooksPath', "core.hooksPath 설정 변경은 금지되어 있습니다"),
        (r'-c\s+commit\.gpgsign=false', "GPG 서명 비활성화는 금지되어 있습니다"),
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
    """Claude Code hook 출력 JSON 생성"""
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
    Claude Code Hook 메인 로직.
    """
    # Sentry 초기화
    sentry_enabled = init_sentry('validate-git-commit', additional_tags={'hook_type': 'pre_tool_use'})

    try:
        add_breadcrumb("Hook execution started", category="lifecycle")

        # stdin에서 JSON 입력 읽기
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

    # Hook 이벤트 확인
    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "PreToolUse":
        add_breadcrumb("Not PreToolUse event, skipping", category="filter")
        flush()
        sys.exit(0)  # 다른 이벤트는 무시

    # Tool 이름 확인
    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        add_breadcrumb("Not Bash tool, skipping", category="filter")
        flush()
        sys.exit(0)  # Bash tool이 아니면 무시

    # 명령어 추출
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")
    add_breadcrumb("Command extracted", category="command", data={"command_preview": command[:100]})

    # Git commit 명령어가 아니면 통과
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

    # 금지된 Git 옵션 확인
    forbidden_errors, git_usage_rules = check_forbidden_git_options(command, config)
    if forbidden_errors:
        add_breadcrumb("Forbidden git options detected", category="validation", level="error", data={"count": len(forbidden_errors)})

        reason = "[ERROR] 금지된 Git 옵션이 감지되었습니다:\n\n"
        for error in forbidden_errors:
            reason += f"  • {error}\n"

        # Add git_usage_rules to the error message if available
        if git_usage_rules:
            reason += "\n[RULES] **프로젝트 Git 사용 규칙:**\n"
            for rule in git_usage_rules:
                reason += f"  • {rule}\n"
        else:
            reason += "\n[TIP] 프로젝트 보안 정책을 준수해 주세요."

        output = create_hook_output("deny", reason)
        print(json.dumps(output))

        flush()
        sys.exit(0)

    # 커밋 메시지 추출
    commit_message = extract_commit_message(command)
    add_breadcrumb("Commit message extracted", category="message", data={"length": len(commit_message) if commit_message else 0})

    # -m 옵션이 없으면 (에디터로 입력하는 경우) 통과
    if not commit_message:
        add_breadcrumb("No commit message (editor mode), skipping validation", category="filter")
        flush()
        sys.exit(0)

    # 커밋 메시지 검증
    add_breadcrumb("Starting commit message validation", category="validation")
    validator = CommitMessageValidator(commit_message, config)
    errors, warnings = validator.validate()

    add_breadcrumb("Validation completed", category="validation", data={
        "errors": len(errors),
        "warnings": len(warnings)
    })

    # 에러가 있으면 차단
    if errors:
        add_breadcrumb("Validation errors found, denying", category="validation", level="error", data={"error_count": len(errors)})

        reason = "[ERROR] 커밋 메시지 검증 실패!\n\n"
        reason += "**오류:**\n"
        for error in errors:
            reason += f"  • {error}\n"

        if warnings:
            reason += "\n**경고:**\n"
            for warning in warnings:
                reason += f"  [WARNING] {warning}\n"

        reason += "\n[TIP] 커밋 메시지를 수정하여 다시 시도하세요."

        output = create_hook_output("deny", reason)
        print(json.dumps(output))

        flush()
        sys.exit(0)

    # 경고만 있으면 자동 차단 (Claude가 수정할 수 있도록)
    if warnings:
        add_breadcrumb("Validation warnings found, denying", category="validation", level="warning", data={"warning_count": len(warnings)})

        reason = "[WARNING] 커밋 메시지 검증 경고!\n\n"
        reason += "**경고:**\n"
        for warning in warnings:
            reason += f"  • {warning}\n"
        reason += "\n[TIP] 커밋 메시지를 개선하여 다시 시도하세요."

        output = create_hook_output("deny", reason)
        print(json.dumps(output))

        flush()
        sys.exit(0)

    # 모든 검증 통과
    add_breadcrumb("All validations passed", category="validation")
    flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
