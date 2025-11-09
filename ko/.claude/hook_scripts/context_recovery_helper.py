#!/usr/bin/env python3
"""
Example Project Context Recovery Helper

압축된 컨텍스트를 자동으로 복구:
1. 복구 상태 파일에서 저장된 요약 로드
2. 요약이 없으면 최근 백업 파일 자동 로드
3. Claude Code CLI로 지능적 요약 생성 (필요시)
4. 새 세션에 맥락 자동 제공
5. ChromaDB 저장 (선택)
"""

import gzip
import json
import os
import signal
import subprocess
import sys
import tempfile
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from common.logger import HookLogger
from common.sentry import init_sentry, capture_exception, add_breadcrumb, flush
from common.config import load_config
from common.formatting import console

# token_manager import 추가
from token_manager import is_continued_session

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box


def find_project_root() -> Optional[Path]:
    """Example Project 프로젝트 루트 자동 탐지

    pyproject.toml에 example_project가 있는 루트 디렉토리를 찾음
    """
    # 1. 환경변수 우선
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        project_path = Path(project_dir)
        if project_path.exists() and (project_path / ".claude").exists():
            return project_path

    # 2. 현재 디렉토리부터 상위로 탐색
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        # pyproject.toml 체크
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding='utf-8')
                if 'example_project' in content.lower() or 'example_project' in content:
                    # .claude 디렉토리가 있는지 확인
                    if (parent / ".claude").exists():
                        return parent
            except Exception:
                pass

        # .git 디렉토리가 있고 .claude 디렉토리가 있는 경우
        if (parent / ".git").exists() and (parent / ".claude").exists():
            return parent

    return None


def load_recovery_state() -> Optional[Dict[str, Any]]:
    """복구 상태 파일 로드"""
    # 프로젝트 루트 자동 탐지
    project_root = find_project_root()

    candidates = []

    # 프로젝트 루트를 찾았으면 우선 사용
    if project_root:
        candidates.append(project_root / ".claude" / "recovery" / "compact-recovery.json")

    # 환경변수 폴백
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        candidates.append(Path(project_dir) / ".claude" / "recovery" / "compact-recovery.json")

    # 기존 후보들 추가
    candidates.extend([
        Path.cwd() / ".claude" / "recovery" / "compact-recovery.json",
        Path.home() / ".claude" / "recovery" / "compact-recovery.json",
    ])

    for candidate in candidates:
        if candidate.exists():
            with open(candidate, 'r', encoding='utf-8') as f:
                return json.load(f)

    return None


def save_recovery_state(state: Dict[str, Any]) -> None:
    """복구 상태 파일 저장

    Args:
        state: 저장할 상태 데이터
    """
    project_root = find_project_root()

    if project_root:
        recovery_file = project_root / ".claude" / "recovery" / "compact-recovery.json"
    else:
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
        if project_dir:
            recovery_file = Path(project_dir) / ".claude" / "recovery" / "compact-recovery.json"
        else:
            recovery_file = Path.cwd() / ".claude" / "recovery" / "compact-recovery.json"

    # 디렉토리 생성
    recovery_file.parent.mkdir(parents=True, exist_ok=True)

    # 저장
    with open(recovery_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def list_backups() -> List[tuple[Path, datetime]]:
    """백업 파일 목록 조회 (JSON, gzip, txt 모두 포함)"""
    # 프로젝트 루트 자동 탐지
    project_root = find_project_root()

    backup_dirs = []

    # 프로젝트 루트를 찾았으면 우선 사용
    if project_root:
        backup_dirs.append(project_root / ".claude" / "backups")

    # 환경변수 폴백
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        backup_dirs.append(Path(project_dir) / ".claude" / "backups")

    # 기존 후보들 추가
    backup_dirs.extend([
        Path.cwd() / ".claude" / "backups",
        Path.home() / ".claude" / "backups",
    ])

    backups = []
    seen_files = set()  # 중복 방지
    for backup_dir in backup_dirs:
        if not backup_dir.exists():
            continue

        # JSON, gzip, txt 모두 찾기
        patterns = ['conversation_*.json', 'conversation_*.json.gz', 'conversation_*.txt']
        for pattern in patterns:
            for backup_file in backup_dir.glob(pattern):
                # 중복 체크 (절대 경로 기준)
                abs_path = backup_file.resolve()
                if abs_path in seen_files:
                    continue
                seen_files.add(abs_path)

                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append((backup_file, mtime))

    return sorted(backups, key=lambda x: x[1], reverse=True)


def load_backup_file(backup_path: Path) -> Optional[Dict[str, Any]]:
    """백업 파일 로드 (JSON 또는 gzip)"""
    try:
        if backup_path.suffix == '.gz':
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:  # type: ignore[assignment]
                return json.load(f)
        elif backup_path.suffix == '.json':
            with open(backup_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 구버전 txt 파일
            return None
    except Exception as e:
        console.print(f"[yellow]WARNING: 백업 파일 로드 실패: {e}[/]")
        return None


def load_summary_from_state(state: Dict[str, Any]) -> Optional[str]:
    """복구 상태 파일에서 저장된 요약 로드

    Args:
        state: 복구 상태 데이터

    Returns:
        저장된 요약 또는 None
    """
    summary = state.get('summary', '')
    if summary and isinstance(summary, str) and len(summary.strip()) > 0:
        return summary.strip()
    return None


def print_recovery_guide(recovery_state: Optional[Dict[str, Any]], collection: str) -> None:
    """컨텍스트 복구 가이드 출력"""
    guide_parts = []

    if recovery_state:
        timestamp = recovery_state.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                guide_parts.append(f"[cyan]마지막 압축 시간:[/] {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except (ValueError, AttributeError):
                pass

        backup_file = recovery_state.get('backup_file')
        if backup_file:
            guide_parts.append(f"[cyan]백업 파일:[/] {backup_file}")

    guide_parts.append(f"[cyan]ChromaDB 컬렉션:[/] {collection}\n")

    # 방법 1
    guide_parts.append("[bold yellow][방법 1] ChromaDB에서 압축된 컨텍스트 검색[/]\n")
    guide_parts.append(f"""chroma:chroma_query_documents(
    collection_name="{collection}",
    query_texts=["컨텍스트 압축 요약"],
    n_results=5,
    where={{"type": "context_compact"}}
)\n""")

    # 방법 2
    guide_parts.append("[bold yellow][방법 2] 백업 파일에서 복구[/]\n")

    backups = list_backups()
    if backups:
        guide_parts.append("[cyan]최근 백업 파일:[/]")
        for i, (backup_path, mtime) in enumerate(backups[:5], 1):
            size = backup_path.stat().st_size
            guide_parts.append(f"   {i}. {backup_path.name}")
            guide_parts.append(f"      시간: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            guide_parts.append(f"      크기: {size:,} bytes")
            guide_parts.append(f"      경로: {backup_path}\n")
    else:
        guide_parts.append("   [yellow]WARNING: 백업 파일을 찾을 수 없습니다.[/]\n")

    # 방법 3
    guide_parts.append("[bold yellow][방법 3] 수동 복구[/]\n")
    guide_parts.append("백업 파일의 내용을 새로운 대화에 다음과 같이 제공:")
    guide_parts.append('   "다음은 이전 대화의 컨텍스트입니다: [백업 내용]"\n')

    guide_parts.append("[dim]Tip: 압축을 방지하려면 .claude/config/auto-compact.json에서")
    guide_parts.append("     enabled를 false로 설정하거나 임계값을 높이세요.[/]")

    console.print(Panel(
        "\n".join(guide_parts),
        title="[bold white]컨텍스트 복구 가이드[/]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    ))


def check_recent_compacts(config: Dict[str, Any], days: int = 7) -> None:
    """최근 압축 이력 확인"""
    collection = config.get('collection', 'example_project_context')

    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    query = f"""chroma:chroma_query_documents(
    collection_name="{collection}",
    query_texts=["컨텍스트 압축"],
    n_results=20,
    where={{
        "type": "context_compact",
        "date": {{"$gte": "{start_date}"}}
    }}
)"""

    content = f"[bold cyan]ChromaDB 쿼리:[/]\n{query}\n\n[dim]Tip: 이 쿼리로 최근 압축된 모든 컨텍스트를 확인할 수 있습니다.[/]"

    console.print(Panel(
        content,
        title=f"[bold white]최근 {days}일 압축 이력 확인[/]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    ))


def list_recovery_files() -> None:
    """복구 관련 파일 확인"""
    project_root = find_project_root()

    files = [
        (".claude/recovery/compact-recovery.json", "복구 상태 파일"),
        (".claude/recovery/recovery-instructions.md", "복구 지침 문서"),
        (".claude/backups/", "백업 디렉토리"),
    ]

    table = Table(
        title="복구 관련 파일",
        show_header=True,
        header_style="bold cyan",
        box=box.SIMPLE
    )

    table.add_column("상태", style="cyan", justify="center")
    table.add_column("파일", style="white")
    table.add_column("설명", style="dim")
    table.add_column("정보", style="yellow")

    for filepath, description in files:
        if project_root:
            full_path = project_root / filepath
        else:
            full_path = Path.cwd() / filepath

        if full_path.exists():
            if full_path.is_file():
                size = full_path.stat().st_size
                mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
                info = f"크기: {size:,} bytes\n수정: {mtime.strftime('%Y-%m-%d %H:%M:%S')}"
                table.add_row("[green]존재[/]", str(filepath), description, info)
            else:
                table.add_row("[green]존재[/]", str(filepath), description, "디렉토리")
        else:
            table.add_row("[red]없음[/]", str(filepath), description, "-")

    console.print(table)


def check_recent_compact(state: Optional[Dict[str, Any]], threshold_hours: int = 24) -> bool:
    """최근에 자동 컴팩트가 발생했는지 확인

    Args:
        state: 복구 상태 데이터
        threshold_hours: 복구 메시지를 표시할 임계값 (시간 단위, 기본 24시간)

    Returns:
        최근 압축 여부
    """
    if not state:
        return False

    # recovered 플래그 체크 - 이미 복구했으면 False 반환
    if state.get('recovered', False):
        return False

    timestamp_str = state.get('timestamp', '')
    if not timestamp_str:
        return False

    try:
        compact_time = datetime.fromisoformat(timestamp_str)

        # UTC 시간인 경우 처리
        if compact_time.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now()

        diff = now - compact_time
        return diff.total_seconds() < (threshold_hours * 3600)
    except Exception:
        return False


def print_quiet_status():
    """복구 필요 없을 때 조용한 상태 메시지"""
    console.print("[green]✓[/green] 정상 세션 시작 (압축 이력 없음)")


@contextmanager
def timeout_context(seconds: int):
    """컨텍스트 관리자로 타임아웃 구현

    Args:
        seconds: 타임아웃 초

    Raises:
        TimeoutError: 타임아웃 발생 시
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f"작업이 {seconds}초 내에 완료되지 않았습니다")

    # 유닉스 계열 시스템에서만 동작
    if hasattr(signal, 'SIGALRM'):
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
    else:
        # Windows 등 SIGALRM 미지원 시스템
        yield


def main():
    """메인 함수 - 자동 맥락 복구"""
    # Sentry 초기화
    init_sentry('context-recovery-helper', additional_tags={'hook_type': 'session_start'})

    # 로거 초기화
    logger = HookLogger("context-recovery-helper") if HookLogger else None

    try:
        if logger:
            logger.log_start()

        add_breadcrumb("Recovery hook execution started", category="lifecycle")

        # 세션 연속성 체크 - 신규 세션인지 확인
        is_new_session = not is_continued_session()
        add_breadcrumb("Session continuity check", category="session", data={"is_new_session": is_new_session})

        if logger:
            logger.log_info("세션 연속성 체크", is_new_session=is_new_session)

        # 연속 세션이면 복구 가이드 출력하지 않음
        if not is_new_session:
            if logger:
                logger.log_end(success=True, status="continued_session")
            sys.exit(0)

        # 신규 세션 - 복구 가이드 출력
        # 설정 로드
        config = load_config('auto-compact.json')
        add_breadcrumb("Config loaded", category="config")

        # 복구 상태 로드
        state = load_recovery_state()
        add_breadcrumb("Recovery state loaded", category="state", data={"has_state": bool(state)})

        # 최근 압축 체크 (12시간 이내)
        recovery_config = config.get('recovery', {})
        threshold_hours = int(recovery_config.get('threshold_hours', 12))
        is_recent_compact = check_recent_compact(state, threshold_hours=threshold_hours)
        add_breadcrumb("Recent compact check", category="compact", data={"is_recent": is_recent_compact})

        # 요약 존재 여부 확인
        summary = state.get('summary') if state else None
        has_summary = bool(summary and summary.strip())

        if logger:
            logger.log_info(
                "복구 상태 확인",
                has_state=bool(state),
                is_recent_compact=is_recent_compact,
                has_summary=has_summary
            )

        # 최근 압축이 없으면 조용히 종료
        if not state or not is_recent_compact:
            if logger:
                logger.log_end(success=True, status="no_recent_compact")
            sys.exit(0)

        # 최근에 자동 컴팩트가 발생한 경우
        # 1. 복구 상태에서 저장된 요약 확인 (auto_compact.py가 저장한 AI 요약)
        add_breadcrumb("Attempting to load summary from state", category="recovery")
        summary = load_summary_from_state(state)

        if not summary:
            # 복구 상태에 요약이 없음 - 비정상 상황
            console.print("[yellow]WARNING: 압축 파일에 요약이 없습니다.[/]")
            console.print("[yellow]다음 세션에 다시 요약이 생성됩니다.[/]")
            print_quiet_status()
            if logger:
                logger.log_end(success=False, status="no_summary_in_state")
            flush()
            sys.exit(0)

        # 요약 출력
        add_breadcrumb("Summary output", category="recovery", data={"length": len(summary)})

        # 명확한 우선순위 지시
        console.print("\n" + "="*80)
        console.print("[bold yellow]IMPORTANT: 아래 한글 요약이 이 세션의 공식 컨텍스트입니다[/bold yellow]")
        console.print("[bold yellow]Claude 자동 생성 영문 요약보다 아래 내용을 우선하세요[/bold yellow]")
        console.print("="*80 + "\n")

        console.print(f"\n{summary}\n")

        # 복구 완료
        console.print("[green]✓[/green] 복구 완료\n")

        # recovered 플래그 추가하여 재복구 방지
        state['recovered'] = True
        state['recovered_at'] = datetime.now().isoformat()
        save_recovery_state(state)

        add_breadcrumb("Recovery completed successfully", category="recovery")

        if logger:
            logger.log_end(success=True, status="recovery_completed", summary_length=len(summary))

        flush()
        sys.exit(0)

    except Exception as e:
        # 에러가 발생해도 세션 시작을 방해하지 않도록
        error_msg = f"복구 헬퍼 실행 중 오류: {e}"
        console.print(f"[yellow]WARNING: {error_msg}[/]")
        console.print("세션을 계속 진행합니다...\n")
        traceback.print_exc(file=sys.stderr)

        # Capture exception to Sentry
        capture_exception(e, context={
            "hook": "context-recovery-helper",
            "error_message": error_msg
        })

        if logger:
            logger.log_end(success=False, error=error_msg)

        flush()
        sys.exit(0)  # 항상 성공으로 종료


if __name__ == "__main__":
    main()
