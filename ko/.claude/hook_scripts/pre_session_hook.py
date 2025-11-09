#!/usr/bin/env python3
"""
Example Project Pre-Session Hook

세션 시작 시 실행되어 다음을 표시:
1. 프로젝트 정보 및 현재 환경
2. ChromaDB 컨텍스트 검색 가이드
3. 작업 규칙 및 지침
4. 완료 체크리스트
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

from common.config import load_config
from common.logger import HookLogger
from common.formatting import (
    console,
    print_rule,
    create_info_table,
    create_rules_table,
)
from rich.panel import Panel
from rich.padding import Padding
from rich.table import Table
from rich import box

from common.servers import SERVER_CONFIG, get_server_status_internal
from token_manager import is_continued_session, should_reset_token_usage


def detect_work_context() -> str:
    """
    현재 작업 컨텍스트 자동 감지 (frontend/backend).
    git status로 수정된 파일들을 분석하여 판단.
    """
    try:
        # 프로젝트 루트에서 실행하도록 cwd 설정
        project_root = Path(__file__).parent.parent.parent

        result = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(project_root)
        )

        if result.returncode != 0:
            return 'backend'  # git 실패시 기본값

        modified_files = result.stdout.strip().split('\n')
        if not modified_files or modified_files == ['']:
            return 'backend'  # 수정된 파일 없으면 기본값

        # 파일 패턴 분석
        frontend_indicators = [
            'app/',  # React 앱
            'components/',
            'pages/',
            'features/',
            '.tsx', '.jsx', '.ts', '.css', '.scss',
            'vite.config', 'tsconfig.json'
        ]

        backend_indicators = [
            'example_project/',  # 메인 백엔드
            '.py',
            'pyproject.toml', 'poetry.lock',
            'alembic/', 'migrations/',
            'tests/integration/', 'tests/unit/'
        ]

        frontend_count = 0
        backend_count = 0

        for line in modified_files:
            if not line.strip():
                continue
            # git status 형식: " M path/to/file" 또는 "?? path/to/file"
            filepath = line[3:].strip() if len(line) > 3 else ''

            # .claude 디렉토리 파일은 스킵
            if '.claude/' in filepath:
                continue

            for indicator in frontend_indicators:
                if indicator in filepath:
                    frontend_count += 1
                    break

            for indicator in backend_indicators:
                if indicator in filepath:
                    backend_count += 1
                    break

        # 프론트엔드 파일이 더 많으면 frontend
        if frontend_count > backend_count:
            return 'frontend'

        return 'backend'

    except Exception:
        return 'backend'  # 예외 발생시 기본값


def detect_environment(config: Dict[str, Any]) -> tuple[str, str]:
    """현재 환경 감지 (Docker/Mac/WSL)"""
    paths = config['project_paths']

    # 현재 작업 디렉토리 확인
    cwd = Path.cwd()

    # Docker 환경
    if str(cwd).startswith(paths.get('docker', '/workspaces/')):
        return 'DOCKER', paths.get('docker', '')

    # WSL 환경
    if str(cwd).startswith('/mnt/c/'):
        return 'WSL', paths.get('wsl', '')

    # Mac 환경
    if str(cwd).startswith('/Users/'):
        return 'MAC', paths.get('mac', '')

    # 알 수 없는 환경
    return 'UNKNOWN', str(cwd)


def print_header(config: Dict[str, Any], env: str, project_path: str, work_context: str) -> None:
    """세션 시작 헤더 출력"""
    collection = config['primary_collection']
    messages = config['messages']

    # 현재 날짜와 시간 (한국 시간)
    now = datetime.now(tz=ZoneInfo('Asia/Seoul'))
    current_date = now.strftime("%Y-%m-%d (%A)")
    current_time = now.strftime("%H:%M:%S")

    console.print()
    print_rule(messages['session_start'], style="bold magenta")

    # 기본 정보 테이블
    info_data = {
        messages['date_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): current_date,
        messages['time_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): current_time,
        messages['environment_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): env,
        messages['project_path_prefix'].replace('📅 ', '').replace('🕐 ', '').replace('📍 ', '').replace('📁 ', ''): project_path,
        messages['work_context_prefix'].replace('🎯 ', ''): work_context.upper(),
    }
    table = create_info_table(info_data)
    console.print(table)

    # 서버 상태 정보
    console.print()
    server_table = Table(
        title="SERVER STATUS",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED
    )
    server_table.add_column("Category", style="cyan")
    server_table.add_column("Type", style="magenta")
    server_table.add_column("Port", justify="right")
    server_table.add_column("Status", justify="center")
    server_table.add_column("PID", justify="right")

    # Backend servers
    for backend_type, config in SERVER_CONFIG["backend"].items():
        is_running, _, pid = get_server_status_internal("backend", backend_type)
        status = "[green]RUNNING[/]" if is_running else "[yellow]STOPPED[/]"
        pid_str = str(pid) if pid else "-"
        server_table.add_row("Backend", backend_type, str(config["port"]), status, pid_str)

    # Frontend servers
    for frontend_type, config in SERVER_CONFIG["frontend"].items():
        is_running, _, pid = get_server_status_internal("frontend", frontend_type)
        status = "[green]RUNNING[/]" if is_running else "[yellow]STOPPED[/]"
        pid_str = str(pid) if pid else "-"
        server_table.add_row("Frontend", frontend_type, str(config["port"]), status, pid_str)

    console.print(server_table)

    print_rule("", style="dim")
    console.print(f"[bold cyan]{messages['chromadb_collection_prefix']}[/bold cyan] [green]{collection}[/green]")
    console.print()


def print_mcp_priority(config: Dict[str, Any]) -> None:
    """MCP 도구 우선순위 출력"""
    priority = config.get('mcp_tools_priority', [])

    if not priority:
        return

    console.print("\n[bold cyan]MCP 도구 우선순위:[/bold cyan]")
    for i, tool in enumerate(priority, 1):
        console.print(f"   [green]{i}.[/green] [white]{tool}[/white]")
    console.print()


def print_context_search_guide(config: Dict[str, Any]) -> None:
    """
    ChromaDB 컨텍스트 자동 검색 안내.
    MCP 도구를 통한 원격 서버 검색 트리거.
    """
    context_search = config['context_search']
    messages = config['messages']
    display = config['display']

    # display.show_context_search 플래그 체크
    if not context_search['enabled'] or not display.get('show_context_search', True):
        return

    collection = context_search['collection']
    queries = context_search['search_queries']
    n_results = context_search['n_results']

    console.print(f"{messages['context_search_guide']}")
    console.print(f"   {messages['collection_label']} {collection}")
    console.print(f"   {messages['results_label']} {n_results}")
    console.print()

    # 핵심: Claude에게 즉시 실행 지시
    console.print("   [yellow]WARNING:[/yellow] 다음 검색을 지금 바로 실행하세요 (필수):")
    console.print()

    # 첫 번째 쿼리로 자동 실행 명령 생성
    if queries:
        first_query = queries[0]
        console.print(f"""   chromadb:chroma_query_documents(
       collection_name="{collection}",
       query_texts=["{first_query}"],
       n_results={n_results}
   )""")
        console.print()

    # 추가 추천 쿼리
    if len(queries) > 1:
        console.print(f"   {messages['recommended_queries']}")
        for query in queries[1:]:
            console.print(f"   - {query}")
        console.print()


def get_project_specific_rules(config: Dict[str, Any]) -> list[str]:
    """
    프로젝트 타입별 특화 규칙 반환.
    모노레포 환경에서 백엔드/프론트엔드 모두 지원.
    """
    project_type = config.get('project_type', '')
    rules = []

    if project_type == 'python_fastapi':
        rules.extend([
            "FastAPI dependency injection 적극 활용",
            "Pydantic 스키마 검증 필수 (schemas 패키지)",
            "Repository/Service 패턴 준수",
            "mypy strict mode 통과 필수",
            "Alembic 마이그레이션 동기화 확인",
        ])

    return rules


def print_guidelines(config: Dict[str, Any]) -> None:
    """
    작업 지침 출력.
    응답 언어, 기본 프롬프트, Sentry 설정 등을 동적으로 표시.
    """
    guidelines = config.get('guidelines', [])
    messages = config['messages']
    display = config['display']
    response_language = config.get('response_language', '한국어')
    default_prompt = config.get('default_prompt', '')

    # Sentry 설정은 settings.json에서 로드
    settings = load_config('settings.json')
    sentry_config = settings.get('sentry', {})

    # display.show_task_instructions 플래그 체크
    if not display.get('show_task_instructions', True):
        return

    # 동적 guidelines 생성
    dynamic_guidelines = []

    # 응답 언어 추가
    dynamic_guidelines.append(f"[LANGUAGE]: {response_language}")

    # 기본 프롬프트 추가
    if default_prompt:
        dynamic_guidelines.append(f"[DEFAULT_PROMPT]: {default_prompt}")

    # Sentry 설정 추가
    if sentry_config.get('enabled'):
        org = sentry_config.get('organization', '')
        projects = sentry_config.get('projects', [])
        if org:
            sentry_info = f"[SENTRY]: Organization={org}"
            if projects:
                sentry_info += f", Projects={', '.join(projects)}"
            dynamic_guidelines.append(sentry_info)

    # 기존 guidelines 추가
    if guidelines:
        dynamic_guidelines.extend(guidelines)

    # 프로젝트 특화 규칙 추가
    project_rules = get_project_specific_rules(config)
    if project_rules:
        dynamic_guidelines.append("")
        dynamic_guidelines.append("[PROJECT]:")
        dynamic_guidelines.extend(project_rules)

    console.print(f"{messages['task_instructions']}")
    for guideline in dynamic_guidelines:
        if guideline:  # 빈 줄은 그냥 출력
            console.print(f"   {guideline}")
        else:
            console.print()
    console.print()


def print_work_rules(config: Dict[str, Any]) -> None:
    """작업 규칙 출력"""
    work_rules = config['work_rules']
    messages = config['messages']

    if not work_rules:
        return

    console.print(f"\n[bold cyan]{messages['work_rules']}[/bold cyan]")
    table = create_rules_table(work_rules)
    console.print(table)
    console.print()


def print_completion_checklist(config: Dict[str, Any]) -> None:
    """완료 체크리스트 출력"""
    checklist = config['completion_checklist']
    messages = config['messages']

    if not checklist:
        return

    console.print(f"\n[bold green]{messages['completion_checklist']}[/bold green]")
    for item in checklist:
        console.print(f"   [green]{item}[/green]")
    console.print()


def print_code_style_rules(config: Dict[str, Any]) -> None:
    """코드 스타일 규칙 출력 (전체 설정 활용)"""
    code_style_rules = config.get('code_style_rules', {})
    messages = config['messages']

    if not code_style_rules:
        return

    console.print(f"{messages['code_style']}")

    # 주석 규칙
    comments = code_style_rules.get('comments', {})
    if comments:
        console.print("   주석:")
        style = comments.get('style', '')
        if style:
            console.print(f"      • Style: {style}")
        language = comments.get('language', '')
        if language:
            console.print(f"      • Language: {language}")

        # forbidden_phrases - 전체 출력
        forbidden_phrases = comments.get('forbidden_phrases', [])
        if forbidden_phrases:
            console.print(f"      • Forbidden phrases: {', '.join(f'{p!r}' for p in forbidden_phrases)}")

        # forbidden_names - 전체 출력
        forbidden_names = comments.get('forbidden_names', [])
        if forbidden_names:
            console.print(f"      • Forbidden names: {', '.join(forbidden_names)}")

        # no_redundant_comments - 출력
        no_redundant = comments.get('no_redundant_comments', '')
        if no_redundant:
            console.print(f"      • {no_redundant}")

    # 아키텍처 규칙 - 전체 출력
    architecture = code_style_rules.get('architecture', {})
    if architecture:
        console.print("   아키텍처:")
        for key, value in architecture.items():
            if isinstance(value, list):
                value_str = ', '.join(str(v) for v in value)
            else:
                value_str = str(value)
            key_display = key.replace('_', ' ').title()
            console.print(f"      • {key_display}: {value_str}")

    console.print()


def print_footer(config: Dict[str, Any]) -> None:
    """세션 시작 푸터 출력"""
    messages = config['messages']

    # 설정에서 가져오기
    critical_checklist = config.get('critical_checklist', {})

    # Critical checklist가 있을 때만 출력
    if not critical_checklist:
        return

    print_rule("", style="dim")
    console.print(f"\n[bold cyan]{messages['start_reminder']}[/bold cyan]\n")

    # 중요 가이드라인 강조 패널
    warning_content = "[bold]중요: 반드시 준수해야 하는 가이드라인 확인[/bold]"
    console.print(
        Panel(
            warning_content,
            style="bold yellow",
            border_style="yellow",
            padding=(0, 2),
        )
    )
    console.print()

    # Critical checklist 섹션별 출력
    section_config = [
        ("required", "필수 사항", "red"),
        ("tools", "도구 사용", "cyan"),
        ("validation", "검증", "magenta"),
        ("important", "중요", "yellow")
    ]

    for section_key, section_title, section_color in section_config:
        items = critical_checklist.get(section_key, [])
        if items:
            console.print(f"   [bold {section_color}][{section_title}][/bold {section_color}]")
            for item in items:
                console.print(f"      • {item}")
            console.print()

    # 숙지 확인 패널
    confirmation_text = """[bold green]위 가이드라인을 충분히 숙지했다면 다음 메시지 출력:[/bold green]

   [cyan]'{{날짜}}-{{시간}} : 컨텍스트 확인 완료'[/cyan]

[bold red]이 메시지를 출력하기 전까지 작업을 시작하지 마세요[/bold red]"""

    console.print(
        Panel(
            confirmation_text,
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()

    console.print(f"[bold green]{messages.get('session_ready', '')}[/bold green]")
    print_rule("", style="bold magenta")
    console.print()


# ====================================================================================================
# 토큰 사용량 표시
# ====================================================================================================

def get_current_token_usage() -> Optional[int]:
    """
    Get current token usage from environment or file.

    Claude Code provides token usage through:
    - Environment variable: CLAUDE_TOKEN_USAGE
    - Temporary file: /tmp/claude-token-usage.txt

    Returns:
        Current token count or None if not available
    """
    # Try environment variable first
    token_env = os.environ.get('CLAUDE_TOKEN_USAGE')
    if token_env:
        try:
            return int(token_env)
        except ValueError:
            pass

    # Try temporary file
    token_file = Path('/tmp/claude-token-usage.txt')
    if token_file.exists():
        try:
            content = token_file.read_text().strip()
            return int(content)
        except (ValueError, OSError):
            pass

    return None


def print_token_status(config: Dict[str, Any]) -> None:
    """
    토큰 사용량 상태 표시 (JSON 기반).

    - 현재 세션 토큰
    - 전체 누적 토큰
    - 경고 및 리셋 가이드
    """
    import json

    # token-usage.json 로드
    usage_path = Path.home() / '.claude' / 'sessions' / 'token-usage.json'
    if not usage_path.exists():
        return

    try:
        with open(usage_path, 'r') as f:
            usage_data = json.load(f)
    except Exception:
        return

    # token-limits.json 로드
    try:
        limits_config = load_config('token-limits.json')
    except FileNotFoundError:
        limits_config = {
            "session_limits": {"warning": 150000, "critical": 180000},
            "total_limits": {"warning": 400000, "critical": 500000}
        }

    if not limits_config.get('enabled', True):
        return

    # 현재 세션 정보
    current_session_id = usage_data.get('current_session', '')
    sessions = usage_data.get('sessions', {})

    if current_session_id not in sessions:
        return

    session_data = sessions[current_session_id]
    current_tokens = session_data.get('tokens', 0)
    total_accumulated = usage_data.get('total_accumulated', 0) + current_tokens

    # 임계값
    session_limits = limits_config.get('session_limits', {})
    total_limits = limits_config.get('total_limits', {})
    display = limits_config.get('display', {})

    session_warning = session_limits.get('warning', 150000)
    session_critical = session_limits.get('critical', 180000)
    total_warning = total_limits.get('warning', 400000)
    total_critical = total_limits.get('critical', 500000)

    # 경고 레벨 판단
    show_warning = False
    is_critical = False

    if current_tokens >= session_critical or total_accumulated >= total_critical:
        is_critical = True
        show_warning = display.get('show_on_critical', True)
    elif current_tokens >= session_warning or total_accumulated >= total_warning:
        show_warning = display.get('show_on_warning', True)

    if not show_warning:
        return

    # 표시
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.panel import Panel

    style = "red bold" if is_critical else "yellow"
    title = "🚨 토큰 사용량 경고" if is_critical else "⚠️  토큰 사용량 알림"

    print_rule(title, style=style)
    console.print()

    # 세션 프로그레스
    session_pct = min(100, int(current_tokens * 100 / session_critical))
    session_color = "red" if current_tokens >= session_critical else "yellow" if current_tokens >= session_warning else "green"

    console.print(f"  [bold]현재 세션:[/bold] {current_tokens:,} / {session_critical:,} tokens ({session_pct}%)")

    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=40, complete_style=session_color),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("", total=session_critical, completed=current_tokens)

    console.print()

    # 전체 누적 프로그레스
    total_pct = min(100, int(total_accumulated * 100 / total_critical))
    total_color = "red" if total_accumulated >= total_critical else "yellow" if total_accumulated >= total_warning else "green"

    console.print(f"  [bold]전체 누적:[/bold] {total_accumulated:,} / {total_critical:,} tokens ({total_pct}%)")

    with Progress(
        TextColumn("  "),
        BarColumn(bar_width=40, complete_style=total_color),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("", total=total_critical, completed=total_accumulated)

    console.print()

    # 리셋 가이드
    if is_critical or total_accumulated >= total_warning:
        console.print(Panel(
            "[yellow]💡 토큰을 리셋하려면:[/yellow]\n"
            "  • 자연어: [cyan]\"토큰 리셋해줘\"[/cyan] 또는 [cyan]\"토큰 초기화\"[/cyan]\n"
            "  • CLI: [cyan]python3 .claude/hook_scripts/reset_tokens.py[/cyan]",
            border_style="yellow",
            padding=(0, 1)
        ))
        console.print()

    print_rule("", style="dim")


# ====================================================================================================
# 컨텍스트 복구 감지 및 안내
# ====================================================================================================

def check_context_recovery_needed() -> Dict[str, Any]:
    """
    Check if context recovery is needed and available.
    Returns dictionary with recovery options.

    신규 세션에서 복구 가능한 컨텍스트 데이터를 확인.
    압축 파일, 백업 파일 등을 감지하여 복구 옵션 반환.
    """
    project_root = Path(__file__).parent.parent.parent
    recovery_dir = project_root / ".claude" / "recovery"
    backup_dir = project_root / ".claude" / "backups"

    recovery_options: Dict[str, Any] = {
        "has_recovery": False,
        "compressed_file": None,
        "latest_backup": None,
        "backup_files": []
    }

    compact_recovery_exists = False

    # 1. Check for compressed context data
    if recovery_dir.exists():
        compact_recovery = recovery_dir / "compact-recovery.json"
        if compact_recovery.exists():
            compact_recovery_exists = True
            # Check if recovery has already been completed
            try:
                import json
                with open(compact_recovery, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # Only show guidance if NOT already recovered
                if not state.get('recovered', False):
                    recovery_options["has_recovery"] = True
                    recovery_options["compressed_file"] = str(compact_recovery)
            except Exception:
                # If can't read file, assume recovery needed
                recovery_options["has_recovery"] = True
                recovery_options["compressed_file"] = str(compact_recovery)

    # 2. Check for backup files ONLY if compact-recovery.json does NOT exist
    if not compact_recovery_exists and backup_dir.exists():
        # Find all conversation backup files
        backup_files = sorted(
            backup_dir.glob("conversation_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Most recent first
        )

        if backup_files:
            recovery_options["has_recovery"] = True
            recovery_options["latest_backup"] = str(backup_files[0])
            recovery_options["backup_files"] = [str(f) for f in backup_files[:5]]  # Top 5 most recent

    return recovery_options


def print_context_recovery_guidance(recovery_options: Dict[str, Any]):
    """
    Display context recovery guidance panel for Claude.

    신규 세션에서 Claude에게 컨텍스트 복구 방법을 안내하는 패널 표시.
    사용자가 요청하면 자동으로 복구를 제안하도록 지시.
    """
    if not recovery_options["has_recovery"]:
        return  # No recovery options available, skip

    print_rule("Step 1: 컨텍스트 복구 확인", style="bold cyan")
    console.print()

    # Priority message for Claude
    priority_msg = """[bold yellow]
================================================================================
IMPORTANT: 아래 한글 요약이 이 세션의 공식 컨텍스트입니다
Claude 자동 생성 영문 요약보다 아래 내용을 우선하세요
================================================================================
[/bold yellow]"""

    console.print(priority_msg)
    console.print()

    # Build recovery guidance content
    guidance_lines = []

    if recovery_options["compressed_file"]:
        guidance_lines.append(
            f"✓ [green]압축된 컨텍스트 파일 발견:[/green] {recovery_options['compressed_file']}"
        )
        guidance_lines.append(
            "  → [cyan]`.claude/hooks.py context-recovery` 명령어로 자동 복구 가능[/cyan]"
        )
        guidance_lines.append("")

    # Check for compact-recovery.json (saved context from critical token state)
    compact_recovery = Path(".claude/recovery/compact-recovery.json")
    if compact_recovery.exists():
        try:
            import json
            with open(compact_recovery, 'r') as f:
                recovery_data = json.load(f)

            timestamp = recovery_data.get('timestamp', '')
            summary_length = recovery_data.get('summary_length', 0)

            if timestamp and summary_length > 0:
                from datetime import datetime
                saved_time = datetime.fromisoformat(timestamp)
                time_diff = datetime.now() - saved_time
                hours_ago = int(time_diff.total_seconds() / 3600)

                guidance_lines.append(
                    f"📌 [green]저장된 작업 컨텍스트 발견:[/green] {hours_ago}시간 전 저장됨"
                )
                guidance_lines.append(
                    "  → [cyan]'이전 작업 계속' 또는 '마지막 작업 확인'을 요청하면 컨텍스트 복구[/cyan]"
                )
                guidance_lines.append("")
        except Exception:
            pass

    if recovery_options["latest_backup"]:
        guidance_lines.append(
            f"✓ [green]최신 백업 파일 발견:[/green] {Path(recovery_options['latest_backup']).name}"
        )
        guidance_lines.append(
            f"  → [cyan]경로: {recovery_options['latest_backup']}[/cyan]"
        )

        if len(recovery_options["backup_files"]) > 1:
            guidance_lines.append(
                f"  → [dim]추가 백업 {len(recovery_options['backup_files'])-1}개 사용 가능[/dim]"
            )
        guidance_lines.append("")

    # Instructions for Claude
    guidance_lines.append("[bold cyan]Claude 지시사항:[/bold cyan]")
    guidance_lines.append("")
    guidance_lines.append(
        "1. [yellow]사용자가 이전 컨텍스트 복구를 요청하면:[/yellow]"
    )
    guidance_lines.append(
        "   - 압축 데이터가 있으면 `.claude/hooks.py context-recovery` 실행"
    )
    guidance_lines.append(
        "   - 압축 데이터가 없으면 최신 백업 파일 읽고 요약"
    )
    guidance_lines.append("")
    guidance_lines.append(
        "2. [yellow]백업 파일 컨벤션:[/yellow]"
    )
    guidance_lines.append(
        "   - JSON 파일에서 'messages' 배열의 내용을 시간순으로 요약"
    )
    guidance_lines.append(
        "   - 작업 목적, 주요 변경사항, 주요 결정, 미완료 작업 중심으로 정리"
    )
    guidance_lines.append("")
    guidance_lines.append(
        "3. [yellow]복구 우선순위:[/yellow] 압축 파일 → 마지막 백업 → 사용자 선택"
    )

    guidance_content = "\n".join(guidance_lines)

    # Display guidance panel
    console.print(
        Panel(
            guidance_content,
            title="[bold green]컨텍스트 복구 안내[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


def main():
    """메인 함수"""
    # 로거 초기화
    logger = HookLogger("pre-session-hook") if HookLogger else None

    try:
        if logger:
            logger.log_start()

        # ========================================
        # Step 0: 세션 연속성 체크 및 토큰 초기화
        # ========================================
        if should_reset_token_usage():
            # 새 세션 시작 - token-usage.json 초기화
            import json
            from datetime import datetime, UTC

            usage_path = Path.home() / '.claude' / 'sessions' / 'token-usage.json'
            usage_path.parent.mkdir(parents=True, exist_ok=True)

            new_data = {
                "current_session": "",
                "sessions": {},
                "total_accumulated": 0,
                "last_reset": datetime.now(UTC).isoformat(),
                "reset_count": 0
            }

            with open(usage_path, 'w') as f:
                json.dump(new_data, f, indent=2)

            if logger:
                logger.log_info("새 세션 감지 - token-usage.json 초기화 완료")

        # 설정 로드
        config = load_config('pre-session.json')

        if logger:
            logger.log_info(
                "설정 로드 완료",
                project_name=config.get('project_name', 'unknown'),
                primary_collection=config.get('primary_collection', 'example_project_context')
            )

        # 환경 감지
        env, project_path = detect_environment(config)

        # 작업 컨텍스트 자동 감지
        work_context = detect_work_context()

        if logger:
            logger.log_info(
                "환경 및 작업 컨텍스트 감지 완료",
                environment=env,
                project_path=project_path,
                work_context=work_context
            )

        # ========================================
        # Step 1: 컨텍스트 복구 확인
        # ========================================
        recovery_options = check_context_recovery_needed()
        if recovery_options["has_recovery"]:
            print_context_recovery_guidance(recovery_options)

            if logger:
                logger.log_info(
                    "컨텍스트 복구 안내 표시 완료",
                    has_compressed=recovery_options["compressed_file"] is not None,
                    has_backup=recovery_options["latest_backup"] is not None,
                    backup_count=len(recovery_options["backup_files"])
                )

        # ========================================
        # Step 2: 프로젝트 정보 및 작업 가이드
        # ========================================
        # Step 1이 출력되지 않았을 때만 Step 2 헤더 출력
        if recovery_options["has_recovery"]:
            print_rule("Step 2: 프로젝트 정보 및 작업 가이드", style="bold cyan")
            console.print()

        # 토큰 상태 표시 (warning 이상일 때만)
        print_token_status(config)

        # 세션 시작 정보 출력
        print_header(config, env, project_path, work_context)
        print_mcp_priority(config)  # MCP 도구 우선순위
        print_context_search_guide(config)  # ChromaDB 자동 검색 트리거
        print_guidelines(config)  # 동적 guidelines + 프로젝트 특화 규칙
        print_work_rules(config)
        print_code_style_rules(config)
        print_completion_checklist(config)
        print_footer(config)

        if logger:
            logger.log_end(
                success=True,
                sections_printed=[
                    "context_recovery" if recovery_options["has_recovery"] else None,
                    "token_status" if get_current_token_usage() else None,
                    "header",
                    "mcp_priority" if config.get('mcp_tools_priority') else None,
                    "context_search" if config['context_search']['enabled'] else None,
                    "guidelines" if config.get('guidelines') else None,
                    "project_rules" if get_project_specific_rules(config) else None,
                    "work_rules" if config.get('work_rules') else None,
                    "code_style_rules" if config.get('code_style_rules') else None,
                    "checklist" if config.get('completion_checklist') else None,
                ]
            )

        sys.exit(0)

    except Exception as e:
        error_msg = f"오류 발생: {e}"
        console.print(f"[red]ERROR:[/red] {error_msg}")
        import traceback
        traceback.print_exc()

        if logger:
            logger.log_end(success=False, error=str(e))

        sys.exit(1)


if __name__ == "__main__":
    main()
