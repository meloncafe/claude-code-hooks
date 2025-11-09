#!/usr/bin/env python3
"""
Claude Code Hook: Session Finish Detector

사용자 프롬프트에서 작업 완료 키워드를 감지하여
세션 마무리 훅 실행을 자동으로 제안합니다.

Hook Event: UserPromptSubmit
"""
import json
import sys
from typing import List

from common.logger import HookLogger
from common.sentry import init_sentry, add_breadcrumb, flush


# 작업 완료를 나타내는 키워드들
FINISH_KEYWORDS: List[str] = [
    "작업 완료",
    "작업완료",
    "작업 끝",
    "작업끝",
    "마무리",
    "끝",
    "완료",
    "finish",
    "done",
    "complete",
    "end session",
    "세션 종료",
    "세션종료",
]


def detect_finish_keyword(prompt: str) -> bool:
    """
    프롬프트에서 작업 완료 키워드 감지.

    Args:
        prompt: 사용자 프롬프트

    Returns:
        키워드가 감지되면 True
    """
    prompt_lower = prompt.lower().strip()

    for keyword in FINISH_KEYWORDS:
        if keyword.lower() in prompt_lower:
            return True

    return False


def create_finish_context() -> str:
    """
    작업 완료 시 Claude에게 전달할 컨텍스트 생성.

    Returns:
        세션 마무리 지시 컨텍스트
    """
    context = """
[SYSTEM] 작업 완료 키워드가 감지되었습니다.

다음을 수행하세요:

1. 모든 작업이 완료되었는지 확인
2. ChromaDB에 작업 내용 저장 여부 확인
3. 테스트 및 타입 체크 통과 확인
4. 위 사항들이 완료되었다면, 세션 마무리 훅을 실행하세요:

   python3 .claude/hook_scripts/post_session_hook.py

이 명령어는 command_restrictor에 의해 사용자 확인을 요청할 것입니다.
사용자가 승인하면 Git 상태, ChromaDB 저장 여부, 완료 체크리스트를 표시합니다.
"""
    return context


def main():
    """메인 함수"""
    logger = HookLogger('detect-session-finish')
    logger.log_start()

    init_sentry(
        'detect-session-finish',
        additional_tags={'hook_type': 'user_prompt_submit'}
    )

    try:
        add_breadcrumb("Hook execution started", category="lifecycle")

        # stdin에서 JSON 입력 읽기
        try:
            input_data = json.load(sys.stdin)
            add_breadcrumb("Input data loaded", category="input")
        except json.JSONDecodeError as e:
            logger.log_error("JSON decode error", error=str(e))
            logger.log_end(success=False)
            flush()
            sys.exit(1)

        # Hook 이벤트 확인
        hook_event = input_data.get("hook_event_name", "")
        if hook_event != "UserPromptSubmit":
            add_breadcrumb("Not UserPromptSubmit event, skipping", category="filter")
            logger.log_end(success=True, skipped=True, reason="not_user_prompt_submit")
            flush()
            sys.exit(0)

        # 프롬프트 추출
        prompt = input_data.get("prompt", "")

        logger.log_info(
            "Checking prompt for finish keywords",
            prompt_preview=prompt[:100]
        )

        # 작업 완료 키워드 감지
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

            # Claude에게 세션 마무리 컨텍스트 추가
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

        # 키워드 없음 - 통과
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
