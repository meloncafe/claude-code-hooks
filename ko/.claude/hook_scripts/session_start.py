#!/usr/bin/env python3
"""
Example Project Session Start Script

세션 시작 시 다음을 순서대로 실행:
1. 터미널 화면 클리어 - 스크롤백 삭제 및 화면 깜빡임 방지
2. Context Recovery Helper - 자동 컴팩트 후 시작인지 체크
3. Pre-Session Hook - 프로젝트 정보 및 작업 가이드 표시

Usage:
    python .claude/session-start.py
"""

import os
import subprocess
import sys
from pathlib import Path

from common.logger import HookLogger, rotate_logs
from common.formatting import console, print_rule


def clear_terminal() -> None:
    """터미널 화면 및 스크롤백 완전 클리어 (Termius 대응)"""
    try:
        # Termius 같은 SSH 클라이언트에서는 서버 측에서 클라이언트
        # 스크롤백을 완전히 제어하기 어렵지만 최선을 다함

        if os.name == 'posix':
            # 방법 1: reset 명령어 (tput reset보다 강력)
            # 완전한 터미널 재초기화
            os.system('reset 2>/dev/null || tput reset 2>/dev/null || clear 2>/dev/null')

            # 방법 2: 여러 ANSI escape codes 조합
            # RIS (Reset to Initial State) - 가장 강력한 리셋
            # print("\033c", end='', flush=True)

            # 스크롤백 버퍼 클리어 시퀀스들
            print("\033[3J", end='', flush=True)  # 스크롤백 버퍼 클리어
            # print("\033[2J", end='', flush=True)  # 화면 클리어
            # print("\033[H", end='', flush=True)   # 커서 홈으로

            # 추가: Erase Saved Lines (일부 터미널에서 지원)
            # print("\033[3J\033[1;1H", end='', flush=True)

    except Exception:
        pass  # 실패해도 세션 시작 방해하지 않음


def get_script_dir() -> Path:
    """스크립트가 위치한 디렉토리 반환"""
    return Path(__file__).parent


def run_script(script_name: str, description: str, logger=None) -> bool:
    """
    스크립트 실행

    Args:
        script_name: 실행할 스크립트 이름
        description: 스크립트 설명
        logger: HookLogger 인스턴스 (선택)

    Returns:
        성공 여부
    """
    script_dir = get_script_dir()
    script_path = script_dir / script_name

    if logger:
        logger.log_info(f"스크립트 실행 시작", script=script_name, description=description)

    if not script_path.exists():
        error_msg = f"{script_name}을 찾을 수 없습니다: {script_path}"
        console.print(f"[yellow][WARNING] {error_msg}[/yellow]")
        if logger:
            logger.log_error(error_msg, script=script_name)
        return False

    # Rich Rule는 pre_session_hook.py에서만 출력하도록 제거
    # (context_recovery_helper는 자체 출력 처리)

    try:
        # capture_output=True로 변경하여 Claude Code가 출력을 캡처할 수 있도록 함
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=True,
            text=True
        )

        # stdout을 직접 출력 (Claude Code가 이를 캡처함)
        if result.stdout:
            print(result.stdout, end='', flush=True)

        # stderr도 출력 (경고/에러 메시지)
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr, flush=True)

        if result.returncode != 0:
            error_msg = f"{script_name} 실행 중 오류 발생 (계속 진행)"
            console.print(f"\n[yellow][WARNING] {error_msg}[/yellow]")
            if logger:
                logger.log_error(error_msg, script=script_name, returncode=result.returncode)
        else:
            if logger:
                logger.log_info(f"스크립트 실행 완료", script=script_name, returncode=result.returncode)

        return True

    except Exception as e:
        error_msg = f"{script_name} 실행 실패: {e}"
        console.print(f"[red][ERROR] {error_msg}[/red]")
        if logger:
            logger.log_error(error_msg, script=script_name, exception=str(e))
        return False


def main():
    """메인 함수"""
    logger = HookLogger("session-start") if HookLogger else None

    try:
        if logger:
            logger.log_start()

        if rotate_logs:
            try:
                rotate_logs(max_files=10)
            except Exception:
                pass

        # 1. Context Recovery Helper 실행
        run_script(
            "context_recovery_helper.py",
            "Step 1: 컨텍스트 복구 확인",
            logger
        )

        # 2. Pre-Session Hook 실행
        run_script(
            "pre_session_hook.py",
            "Step 2: 프로젝트 정보 및 작업 가이드",
            logger
        )

        # 최종 메시지는 pre-session-hook에서 출력하므로 여기서는 생략

        if logger:
            logger.log_end(success=True)

        sys.exit(0)

    except Exception as e:
        if logger:
            logger.log_end(success=False, error=str(e))
        raise


if __name__ == "__main__":
    main()
