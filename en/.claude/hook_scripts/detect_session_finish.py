#!/usr/bin/env python3
"""
Claude Code Hook: Session Finish Detector

Detects task completion keywords in user prompts to automatically suggest executing session-ending hooks.

Hook Event: UserPromptSubmit
"""
import json
import sys
from typing import List

from common.logger import HookLogger
from common.sentry import init_sentry, add_breadcrumb, flush


# 작업 완료를 나타내는 키워드들
FINISH_KEYWORDS: List[str] = [
    "finish",
    "done",
    "complete",
    "end session",
    "세션 종료",
    "세션종료",
]


def detect_finish_keyword(prompt: str) -> bool:
    """
    Detect completion keywords in the prompt.

    Args:
        prompt: User prompt

    Returns:
        True if keywords are detected
    """
    prompt_lower = prompt.lower().strip()

    for keyword in FINISH_KEYWORDS:
        if keyword.lower() in prompt_lower:
            return True

    return False


def create_finish_context() -> str:
    """
    Generate context to pass to Claude upon task completion.

    Returns:
        Context instructing session closure
    """
    context = """
[SYSTEM] The task completion keyword has been detected.

Please perform the following:

1. Verify that all tasks are complete
2. Confirm whether the task details have been saved to ChromaDB
3. Verify tests and type checks passed
4. If the above steps are complete, run the session closure hook:

   python3 .claude/hook_scripts/post_session_hook.py

This command will prompt for user confirmation via command_restrictor.
Upon user approval, it displays Git status, ChromaDB save status, and the completion checklist.
"""
    return context


def main():
    """Main Function"""
    logger = HookLogger('detect-session-finish')
    logger.log_start()

    init_sentry(
        'detect-session-finish',
        additional_tags={'hook_type': 'user_prompt_submit'}
    )

    try:
        add_breadcrumb("Hook execution started", category="lifecycle")

        try:
            input_data = json.load(sys.stdin)
            add_breadcrumb("Input data loaded", category="input")
        except json.JSONDecodeError as e:
            logger.log_error("JSON decode error", error=str(e))
            logger.log_end(success=False)
            flush()
            sys.exit(1)

        hook_event = input_data.get("hook_event_name", "")
        if hook_event != "UserPromptSubmit":
            add_breadcrumb("Not UserPromptSubmit event, skipping", category="filter")
            logger.log_end(success=True, skipped=True, reason="not_user_prompt_submit")
            flush()
            sys.exit(0)

        prompt = input_data.get("prompt", "")

        logger.log_info(
            "Checking prompt for finish keywords",
            prompt_preview=prompt[:100]
        )

        if detect_finish_keyword(prompt):
            logger.log_info(
                "Finish keyword detected",
                prompt_preview=prompt[:100]
            )
            add_breadcrumb(
                "Finish keyword detected",
                category="detection",
                data={"prompt_preview": prompt[:100]}
            )

            context = create_finish_context()

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context
                }
            }

            print(json.dumps(output))
            logger.log_end(success=True, action="context_added")
            flush()
            sys.exit(0)

        add_breadcrumb("No finish keyword detected", category="detection")
        logger.log_end(success=True, action="passed")
        flush()
        sys.exit(0)

    except Exception as e:
        logger.log_error("Unexpected error", error=str(e))
        logger.log_end(success=False)
        flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
