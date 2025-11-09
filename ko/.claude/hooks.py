#!/usr/bin/env python3
"""
Example Project Hook Scripts CLI Manager

통합 CLI로 모든 hook scripts를 수동 실행 및 관리.
"""
import sys
from pathlib import Path

# hook_scripts 디렉토리를 Python 경로에 추가
HOOK_SCRIPTS_DIR = Path(__file__).parent / "hook_scripts"
sys.path.insert(0, str(HOOK_SCRIPTS_DIR))

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="hooks",
    help="Example Project Hook Scripts 통합 관리 CLI",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def session_start(
    skip_recovery: bool = typer.Option(
        False,
        "--skip-recovery",
        help="컨텍스트 복구 단계 건너뛰기"
    ),
    skip_guide: bool = typer.Option(
        False,
        "--skip-guide",
        help="프로젝트 가이드 표시 건너뛰기"
    )
):
    """
    세션 시작 - 컨텍스트 복구 및 프로젝트 가이드 표시

    자동으로 실행:
    1. Context Recovery Helper (컨텍스트 복구)
    2. Pre-Session Hook (프로젝트 정보 및 가이드)
    """
    from session_start import main as session_start_main

    console.print("[cyan]세션 시작 중...[/cyan]")
    try:
        session_start_main()
    except SystemExit:
        pass


@app.command()
def context_recovery():
    """
    컨텍스트 복구 실행

    압축된 컨텍스트를 자동으로 복구:
    - 복구 상태 파일에서 저장된 요약 로드
    - 최근 백업 파일 자동 로드
    - 새 세션에 맥락 자동 제공
    """
    from context_recovery_helper import main as recovery_main

    console.print("[cyan]컨텍스트 복구 중...[/cyan]")
    try:
        recovery_main()
    except SystemExit:
        pass


@app.command()
def pre_session():
    """
    프로젝트 정보 및 작업 가이드 표시

    세션 시작 시 표시:
    - 프로젝트 정보 및 현재 환경
    - ChromaDB 컨텍스트 검색 가이드
    - 작업 규칙 및 지침
    - 완료 체크리스트
    """
    from pre_session_hook import main as pre_session_main

    console.print("[cyan]프로젝트 가이드 표시 중...[/cyan]")
    try:
        pre_session_main()
    except SystemExit:
        pass


@app.command()
def auto_compact(
    threshold: float = typer.Option(
        None,
        "--threshold",
        help="압축 임계값 (0.0-1.0)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="강제 압축 실행"
    )
):
    """
    자동 컨텍스트 압축

    컨텍스트가 임계값을 초과하면 자동으로:
    - 백업 생성
    - AI 요약 생성
    - ChromaDB에 저장
    - 복구 파일 생성
    """
    console.print("[cyan]컨텍스트 압축 확인 중...[/cyan]")
    console.print("[yellow]Note: PreCompact hook으로 실행해야 정상 작동합니다[/yellow]")


@app.command()
def post_session():
    """
    세션 종료 후 정리

    세션 종료 시 실행:
    - 임시 파일 정리
    - 로그 정리
    - 상태 저장
    """
    from post_session_hook import main as post_session_main

    console.print("[cyan]세션 종료 처리 중...[/cyan]")
    try:
        post_session_main()
    except SystemExit:
        pass


@app.command()
def validate_commit(
    message: str = typer.Argument(
        None,
        help="검증할 커밋 메시지 (미제공시 stdin에서 읽음)"
    )
):
    """
    Git 커밋 메시지 검증

    검증 항목:
    - Conventional Commits 형식
    - 메시지 길이
    - 금지 패턴 체크
    - Co-authored 규칙
    """
    from validate_git_commit import main as validate_main

    if message:
        # 메시지를 stdin으로 제공
        import io
        sys.stdin = io.StringIO(message)

    console.print("[cyan]커밋 메시지 검증 중...[/cyan]")
    try:
        validate_main()
    except SystemExit as e:
        if e.code != 0:
            console.print("[red]검증 실패[/red]")
        else:
            console.print("[green]검증 통과[/green]")


@app.command()
def scan_secrets(
    path: str = typer.Argument(".", help="스캔할 경로"),
    staged_only: bool = typer.Option(False, "--staged", help="staged 파일만 스캔")
):
    """
    시크릿 및 민감 정보 스캔

    검사 항목:
    - API 키 패턴
    - 비밀번호 패턴
    - 토큰 패턴
    - 민감한 파일명
    """
    import subprocess
    import json

    console.print(f"[cyan]시크릿 스캔 중: {path}[/cyan]")

    # secret_scanner.py는 PreToolUse hook으로 설계됨
    # stdin으로 JSON 전달
    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": path}
    }

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPTS_DIR / "secret_scanner.py")],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr, style="dim")

        if result.returncode != 0:
            console.print(f"[yellow]경고: 스캔 중 오류 발생 (exit code: {result.returncode})[/yellow]")
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")


@app.command()
def check_mocks(
    path: str = typer.Argument(".", help="검사할 경로")
):
    """
    Mock 코드 및 플레이스홀더 체크

    검사 항목:
    - TODO 주석
    - Mock 데이터
    - 플레이스홀더 코드
    - 미구현 함수
    """
    import subprocess
    import json

    console.print(f"[cyan]Mock 코드 체크 중: {path}[/cyan]")

    # no_mock_code.py는 PreToolUse hook으로 설계됨
    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": path}
    }

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPTS_DIR / "no_mock_code.py")],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr, style="dim")

        if result.returncode != 0:
            console.print(f"[yellow]경고: 체크 중 오류 발생 (exit code: {result.returncode})[/yellow]")
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")


@app.command()
def validate_timestamp():
    """
    코드 내 타임스탬프 검증

    검증 항목:
    - 하드코딩된 날짜
    - 오래된 타임스탬프
    - 만료된 시간 값
    """
    import subprocess
    import json

    console.print("[cyan]타임스탬프 검증 중...[/cyan]")

    # timestamp_validator.py는 PreToolUse hook으로 설계됨
    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {}
    }

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPTS_DIR / "timestamp_validator.py")],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr, style="dim")

        if result.returncode != 0:
            console.print(f"[yellow]경고: 검증 중 오류 발생 (exit code: {result.returncode})[/yellow]")
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")


@app.command()
def view_logs(
    script: str = typer.Argument(None, help="스크립트 이름 (예: session_start)"),
    limit: int = typer.Option(20, "--limit", "-n", help="조회할 로그 개수"),
    errors: bool = typer.Option(False, "--errors", "-e", help="에러만 표시"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력")
):
    """훅 로그 조회"""
    import subprocess

    # view_logs.py의 view 서브커맨드를 직접 실행
    cmd = [sys.executable, str(HOOK_SCRIPTS_DIR / "view_logs.py"), "view"]
    if script:
        cmd.append(script)
    cmd.extend(["--limit", str(limit)])
    if errors:
        cmd.append("--errors")
    if json_output:
        cmd.append("--json")

    subprocess.run(cmd)


@app.command()
def server(
    action: str = typer.Argument(..., help="서버 액션: list, status, start-backend, start-frontend, stop, stop-all"),
    category: str = typer.Argument(None, help="서버 카테고리 (backend/frontend) 또는 타입"),
    server_type: str = typer.Argument(None, help="서버 타입 (main/auth/auth-example)")
):
    """
    개발 서버 관리

    액션:
    - list: 모든 서버 상태 확인
    - status <category> <type>: 서버 상태 확인
    - start-backend [type]: 백엔드 서버 시작 (기본값: auth-example)
    - start-frontend [type]: 프론트엔드 서버 시작 (기본값: auth-example)
    - stop <category> <type>: 서버 중지
    - stop-all: 모든 실행 중인 서버 중지

    예시:
        .claude/hooks server list
        .claude/hooks server status backend auth-example
        .claude/hooks server start-backend auth-example
        .claude/hooks server start-backend main
        .claude/hooks server start-frontend
        .claude/hooks server stop backend auth-example
        .claude/hooks server stop-all
    """
    import subprocess

    # common/servers.py를 직접 실행
    cmd = [sys.executable, str(HOOK_SCRIPTS_DIR / "common" / "servers.py"), action]

    # start-backend, start-frontend: category를 타입으로 사용
    if action in ["start-backend", "start-frontend"]:
        if category:
            cmd.append(category)

    # status, stop: category와 type 둘 다 필요
    elif action in ["status", "stop"]:
        if not category or not server_type:
            console.print(f"[red]오류: {action}는 <category> <type> 형식이 필요합니다[/red]")
            console.print(f"[yellow]예시: .claude/hooks server {action} backend auth-example[/yellow]")
            raise typer.Exit(1)
        cmd.append(category)
        cmd.append(server_type)

    subprocess.run(cmd)


@app.command()
def list_hooks():
    """
    사용 가능한 모든 훅 스크립트 목록 표시
    """
    table = Table(title="Hook Scripts", show_header=True, header_style="bold cyan")
    table.add_column("Command", style="green")
    table.add_column("Description", style="white")
    table.add_column("Type", style="yellow")

    hooks = [
        ("session-start", "세션 시작 (복구 + 가이드)", "Lifecycle"),
        ("context-recovery", "컨텍스트 복구", "Lifecycle"),
        ("pre-session", "프로젝트 가이드 표시", "Lifecycle"),
        ("auto-compact", "자동 컨텍스트 압축", "Lifecycle"),
        ("post-session", "세션 종료 정리", "Lifecycle"),
        ("validate-commit", "커밋 메시지 검증", "Git"),
        ("scan-secrets", "시크릿 스캔", "Security"),
        ("check-mocks", "Mock 코드 체크", "Quality"),
        ("validate-timestamp", "타임스탬프 검증", "Quality"),
        ("view-logs", "훅 로그 조회", "Utility"),
        ("server", "개발 서버 관리", "Dev"),
        ("token-status", "토큰 사용량 상태", "Token"),
        ("token-reset", "토큰 카운터 리셋", "Token"),
        ("token-extract", "토큰 추출 (PostToolUse Hook)", "Token"),
        ("token-check", "세션 연속성 체크", "Token"),
    ]

    for cmd, desc, type_ in hooks:
        table.add_row(cmd, desc, type_)

    console.print(table)
    console.print("\n[dim]자세한 정보: .claude/hooks [command] --help[/dim]")


@app.command()
def token_status():
    """
    토큰 사용량 현재 상태 표시

    Shows:
    - Current session tokens
    - Total accumulated tokens
    - Progress bars and thresholds
    """
    from token_manager import status as token_status_cmd

    try:
        token_status_cmd()
    except SystemExit:
        pass


@app.command()
def token_reset(
    delete_sessions: bool = typer.Option(
        False,
        "--delete-sessions",
        help="세션 기록을 아카이브가 아닌 삭제"
    )
):
    """
    토큰 사용량 카운터 리셋

    기본적으로 세션 기록을 아카이브하며,
    --delete-sessions 플래그로 완전 삭제 가능
    """
    from token_manager import reset as token_reset_cmd

    try:
        token_reset_cmd(delete_sessions=delete_sessions)
    except SystemExit:
        pass


@app.command()
def token_extract():
    """
    PostToolUse Hook - 토큰 추출 및 업데이트

    자동으로 호출되어 세션 파일에서 토큰 사용량을 추출하고 업데이트
    """
    from token_manager import extract as token_extract_cmd

    try:
        token_extract_cmd()
    except SystemExit:
        pass


@app.command()
def token_check():
    """
    세션 연속성 체크

    현재 세션이 이전 세션의 연속인지 확인
    (claude vs claude --continue 구분)
    """
    from token_manager import check_continuity as token_check_cmd

    try:
        token_check_cmd()
    except SystemExit:
        pass


@app.callback()
def main():
    """
    Example Project Hook Scripts CLI Manager

    모든 hook scripts를 통합 관리하는 CLI 도구.
    각 명령어의 자세한 사용법은 --help 옵션으로 확인하세요.

    예시:
        .claude/hooks session-start
        .claude/hooks validate-commit "feat: new feature"
        .claude/hooks view-logs --follow
        .claude/hooks server start --service backend
    """
    pass


if __name__ == "__main__":
    app()
