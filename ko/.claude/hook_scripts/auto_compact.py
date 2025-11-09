#!/usr/bin/env python3
"""
Example Project Auto-Compact Script

컨텍스트가 너무 커질 때 자동으로:
1. 현재 대화 내용 완전 백업 (jsonl 파싱)
2. Claude Code로 지능적 요약 생성
3. ChromaDB에 저장
4. 복구 정보 저장
"""

import gzip
import json
import os
import select
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich import box

from common.config import load_auto_compact_config
from common.logger import HookLogger
from common.sentry import init_sentry, capture_exception, add_breadcrumb, flush

console = Console(stderr=True)


def find_project_root() -> Optional[Path]:
    """
    Example Project 프로젝트 루트 자동 탐지

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


def parse_transcript_jsonl(transcript_path: Path) -> Dict[str, Any]:
    """jsonl 파일 파싱하여 구조화된 데이터 반환"""
    messages = []
    file_history = {'snapshots': [], 'tracked_files': {}}

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get('type')

                if entry_type == 'user':
                    msg = entry.get('message', {})
                    messages.append({
                        'uuid': entry.get('uuid'),
                        'type': 'user',
                        'timestamp': entry.get('timestamp'),
                        'content': msg.get('content', ''),
                        'metadata': {
                            'cwd': entry.get('cwd'),
                            'git_branch': entry.get('git_branch'),
                            'is_sidechain': entry.get('isSidechain', False)
                        }
                    })

                elif entry_type == 'assistant':
                    msg = entry.get('message', {})
                    messages.append({
                        'uuid': entry.get('uuid'),
                        'type': 'assistant',
                        'timestamp': entry.get('timestamp'),
                        'content': msg.get('content', []),
                        'model': msg.get('model'),
                        'usage': msg.get('usage', {}),
                        'stop_reason': msg.get('stop_reason')
                    })

                elif entry_type == 'file-history-snapshot':
                    snapshot = entry.get('snapshot', {})
                    file_history['snapshots'].append({
                        'message_id': snapshot.get('messageId'),
                        'timestamp': snapshot.get('timestamp'),
                        'tracked_files': snapshot.get('trackedFileBackups', {})
                    })

    except FileNotFoundError:
        console.print(f"[yellow]WARNING: Transcript 파일을 찾을 수 없습니다: {transcript_path}[/]")
    except Exception as e:
        console.print(f"[yellow]WARNING: Transcript 파싱 중 오류: {e}[/]")

    return {
        'messages': messages,
        'file_history': file_history
    }


def calculate_statistics(conversation_data: Dict[str, Any]) -> Dict[str, Any]:
    """대화 통계 계산"""
    messages = conversation_data.get('messages', [])

    user_messages = [m for m in messages if m.get('type') == 'user']
    assistant_messages = [m for m in messages if m.get('type') == 'assistant']

    total_tokens = 0
    for msg in assistant_messages:
        usage = msg.get('usage', {})
        total_tokens += usage.get('input_tokens', 0)
        total_tokens += usage.get('output_tokens', 0)
        total_tokens += usage.get('cache_read_input_tokens', 0)

    # 대화 시간 계산
    if messages:
        first_ts = messages[0].get('timestamp', '')
        last_ts = messages[-1].get('timestamp', '')
        try:
            first_dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
            last_dt = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            duration_seconds = (last_dt - first_dt).total_seconds()
        except (ValueError, AttributeError):
            duration_seconds = 0
    else:
        duration_seconds = 0

    return {
        'total_messages': len(messages),
        'user_messages': len(user_messages),
        'assistant_messages': len(assistant_messages),
        'total_tokens': total_tokens,
        'conversation_duration_seconds': int(duration_seconds),
        'file_snapshots': len(conversation_data.get('file_history', {}).get('snapshots', []))
    }


def backup_conversation(
    conversation: str,
    config: Dict[str, Any]
) -> tuple[Optional[Path], Optional[Dict[str, Any]]]:
    """
    대화 내용 완전 백업 (jsonl 파싱 포함)

    Returns:
        (backup_file, backup_data) 튜플
    """
    backup_config = config['backup']

    if not backup_config['enabled']:
        return None, None

    # 프로젝트 루트 기준 백업 경로 사용
    project_root = find_project_root()
    if project_root:
        backup_location = project_root / ".claude" / "backups"
    else:
        backup_location = Path(backup_config['backup_location'])

    backup_location.mkdir(parents=True, exist_ok=True)

    # stdin JSON 파싱
    try:
        session_meta = json.loads(conversation)
    except json.JSONDecodeError:
        console.print("[yellow]WARNING: 세션 메타데이터 파싱 실패, 텍스트로 백업합니다.[/]")
        # 기존 방식으로 폴백
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_location / f"conversation_{timestamp}.txt"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(conversation)
        return backup_file, None

    # transcript_path 추출 및 파싱
    transcript_path = Path(session_meta.get('transcript_path', ''))

    if not transcript_path.exists():
        console.print(f"[yellow]WARNING: Transcript 파일이 존재하지 않습니다: {transcript_path}[/]")
        conversation_data = {'messages': [], 'file_history': {}}
    else:
        conversation_data = parse_transcript_jsonl(transcript_path)

    # 완전한 백업 구조 생성
    backup_data = {
        'backup_metadata': {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'session_id': session_meta.get('session_id'),
            'cwd': session_meta.get('cwd'),
            'git_branch': session_meta.get('git_branch'),
            'original_transcript_path': str(transcript_path),
            'hook_event': session_meta.get('hook_event_name'),
            'trigger': session_meta.get('trigger')
        },
        'conversation': conversation_data['messages'],
        'file_history': conversation_data['file_history'],
        'statistics': calculate_statistics(conversation_data)
    }

    # JSON으로 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 압축 옵션 확인
    use_compression = backup_config['compress']

    if use_compression:
        backup_file = backup_location / f"conversation_{timestamp}.json.gz"
        with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)  # type: ignore[arg-type]
    else:
        backup_file = backup_location / f"conversation_{timestamp}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

    console.print(f"[green]OK[/] 백업 생성: {backup_file}")
    console.print(f"   메시지: {backup_data['statistics']['total_messages']}개")
    console.print(f"   토큰: {backup_data['statistics']['total_tokens']:,}")
    console.print(f"   기간: {backup_data['statistics']['conversation_duration_seconds']}초")

    # 오래된 백업 정리
    max_backups = backup_config['max_backups']
    cleanup_old_backups(backup_location, max_backups)

    return backup_file, backup_data


def cleanup_old_backups(backup_dir: Path, max_backups: int) -> None:
    """오래된 백업 파일 정리"""
    # JSON과 압축 파일 모두 찾기
    backups = sorted(backup_dir.glob('conversation_*.*'))

    if len(backups) > max_backups:
        for backup in backups[:-max_backups]:
            backup.unlink()
            console.print(f"삭제: {backup.name}")


def clean_backup_for_summary(backup_data: Dict[str, Any], keep_recent: int = 10) -> Dict[str, Any]:
    """요약 생성을 위해 백업 데이터 정제

    최근 N개 메시지만 보존하여 컨텍스트 크기 대폭 감소:
    - 최근 N개 메시지만 완전 보존
    - 나머지는 완전 제거
    - 5MB → 수십KB로 압축 (99% 이상)

    Args:
        backup_data: 원본 백업 데이터
        keep_recent: 완전히 보존할 최근 메시지 수

    Returns:
        정제된 백업 데이터
    """
    messages = backup_data.get('conversation', [])
    if not messages:
        return backup_data

    # 최근 N개 메시지만 보존
    total_messages = len(messages)
    cleaned_messages = messages[-keep_recent:] if total_messages > keep_recent else messages

    # 정제된 데이터 생성
    cleaned_backup = {
        'backup_metadata': backup_data.get('backup_metadata', {}),
        'conversation': cleaned_messages,
        'file_history': {'snapshots': []},  # 파일 히스토리는 제거
        'statistics': backup_data.get('statistics', {})
    }

    return cleaned_backup


def format_conversation_for_claude(messages: List[Dict[str, Any]]) -> str:
    """Claude CLI에 전달할 대화 내용 포맷팅"""
    formatted = []

    for msg in messages:
        msg_type = msg.get('type')
        timestamp = msg.get('timestamp', '')

        if msg_type == 'user':
            content = msg.get('content', '')
            if isinstance(content, str) and content.strip():
                formatted.append(f"[User - {timestamp}]\n{content}\n")

        elif msg_type == 'assistant':
            content = msg.get('content', [])
            text_parts = []

            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif item.get('type') == 'tool_use':
                            tool_name = item.get('name', '')
                            tool_input = item.get('input', {})
                            text_parts.append(f"[Tool: {tool_name}]\n{tool_input}")

            if text_parts:
                text = '\n'.join(text_parts)
                formatted.append(f"[Assistant - {timestamp}]\n{text}\n")

    return '\n---\n'.join(formatted)


def generate_claude_cli_summary(
    backup_data: Dict[str, Any],
    config: Dict[str, Any]
) -> Optional[str]:
    """
    Claude Code CLI를 사용한 지능적 요약 생성 (Haiku 4.5 모델 사용)

    Claude Haiku 4.5를 사용하여 빠르고 비용 효율적인 요약 생성:
    - 속도: Sonnet 4 대비 2배 이상 빠름
    - 비용: Sonnet 4 대비 1/3 수준 ($1/$5 per million tokens)
    - 성능: Sonnet 4와 유사한 코딩 성능

    Args:
        backup_data: 백업된 대화 데이터
        config: 설정

    Returns:
        요약 문자열 또는 None (실패 시)
    """
    # 1차 정제: 백업 데이터에서 불필요한 부분 제거
    strategy = config['compact_strategy']
    keep_recent = strategy.get('keep_recent_messages', 10)

    cleaned_backup = clean_backup_for_summary(backup_data, keep_recent=keep_recent)

    messages = cleaned_backup.get('conversation', [])
    if not messages:
        return None

    metadata = backup_data.get('backup_metadata', {})
    statistics = backup_data.get('statistics', {})
    focus_areas = strategy.get('focus_areas', ['작업', '결정사항', '코드 변경'])

    # 대화 내용 포맷팅
    conversation_text = format_conversation_for_claude(messages)

    # Claude CLI에 전달할 프롬프트 생성
    prompt = f"""다음 개발 세션을 **5000자 이내로 간결하게** 요약해주세요.

## 세션 정보
[{focus_areas}] | 세션: {metadata.get('session_id', 'N/A')[:8]}... | 브랜치: {metadata.get('git_branch', 'N/A')} | 메시지: {statistics.get('total_messages', 0)}개 | 시간: {statistics.get('conversation_duration_seconds', 0)//60}분

## 요약 규칙 (중요!)
1. **5000자 이내 필수** - 불렛포인트 위주, 간결하게
2. 핵심만: 작업 목적 → 주요 변경 → 결정사항 → 미완료
3. 코드는 파일명:라인만 (코드 블록 최소화)
4. 불필요한 설명, 반복, 배경 제거

## 요약 형식
# 이전 세션 요약 (작업 디렉토리: {metadata.get('cwd', 'N/A')})

## 작업 목적
[1-2줄로 핵심 목표]

## 주요 변경사항
- 파일명:라인 - [변경 내용 1줄]

## 주요 결정
- [결정사항 1줄]

## 미완료/다음 단계
- [TODO 항목]

---

## 대화 내용
{conversation_text}

위 대화의 핵심만 추출하여 5000자 이내로 요약하세요. 불필요한 설명은 제거하고 작업 컨텍스트 복구에 필요한 정보만 남기세요."""

    try:
        # Claude CLI 실행 (Haiku 4.5 모델 사용)
        console.print("[cyan]AI[/] Claude Haiku 4.5로 빠른 요약 생성 중...")

        # 임시 파일에 프롬프트 저장
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            temp_file = f.name

        # Claude CLI 실행 (print mode with JSON output)
        # MCP 서버 비활성화를 위해 빈 설정 파일과 strict 모드 사용
        # Haiku 4.5 모델로 속도 2배 향상, 비용 1/3 절감
        empty_mcp_config = Path(__file__).parent.parent / "config" / "empty-mcp-config.json"
        cmd = [
            'claude',
            '-p',  # print mode
            '--model', 'claude-haiku-4-5',  # Haiku 4.5 모델 사용 (빠르고 저렴)
            '--mcp-config', str(empty_mcp_config),  # 빈 MCP 설정 사용
            '--strict-mcp-config',  # 전역 MCP 설정 무시 (Serena 등 실행 방지)
            '--dangerously-skip-permissions',  # 권한 자동 승인
            '--output-format', 'json'
        ]

        # 프롬프트를 stdin으로 전달
        with open(temp_file, 'r', encoding='utf-8') as prompt_file:
            result = subprocess.run(
                cmd,
                stdin=prompt_file,
                capture_output=True,
                text=True,
                timeout=180  # 3분 타임아웃으로 단축
            )

        # 임시 파일 삭제
        Path(temp_file).unlink(missing_ok=True)

        if result.returncode != 0:
            console.print(f"[yellow]WARNING: Claude CLI 실행 실패 (exit code: {result.returncode})[/]")
            console.print(f"   stderr: {result.stderr[:500]}")
            console.print(f"   stdout: {result.stdout[:500]}")
            return None

        # JSON 출력 파싱
        try:
            output_data = json.loads(result.stdout)
            # Claude CLI 응답 추출
            summary = ""

            if isinstance(output_data, list):
                # 배열에서 type='result'인 항목 찾기
                for item in output_data:
                    if isinstance(item, dict) and item.get('type') == 'result':
                        summary = item.get('result', '')
                        break

                # result 타입이 없으면 assistant 메시지에서 추출
                if not summary:
                    for item in output_data:
                        if isinstance(item, dict) and item.get('type') == 'assistant':
                            message = item.get('message', {})
                            content = message.get('content', [])
                            if isinstance(content, list):
                                for content_item in content:
                                    if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                        summary = content_item.get('text', '')
                                        break
                            break
            elif isinstance(output_data, dict):
                # 폴백: 단일 객체인 경우
                summary = output_data.get('result', '')
                if not summary:
                    summary = output_data.get('content', '')
                    if isinstance(summary, list):
                        text_parts = []
                        for item in summary:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                        summary = '\n'.join(text_parts)
            else:
                summary = str(output_data)

            if summary and len(summary.strip()) > 0:
                console.print("[green]OK[/] Claude CLI 요약 생성 완료")
                return summary.strip()
            else:
                console.print("[yellow]WARNING: Claude CLI 응답이 비어있습니다.[/]")
                console.print(f"   output_data type: {type(output_data)}")
                console.print(f"   output_data preview: {str(output_data)[:500]}")
                return None

        except json.JSONDecodeError:
            # JSON 파싱 실패 시 stdout을 그대로 사용
            if result.stdout.strip():
                console.print("[green]OK[/] Claude CLI 요약 생성 완료 (text mode)")
                return result.stdout.strip()
            return None

    except subprocess.TimeoutExpired:
        console.print("[yellow]WARNING: Claude CLI 실행 타임아웃[/]")
        Path(temp_file).unlink(missing_ok=True)
        return None
    except FileNotFoundError:
        console.print("[yellow]WARNING: Claude CLI를 찾을 수 없습니다. 'claude' 명령어가 PATH에 있는지 확인하세요.[/]")
        return None
    except Exception as e:
        console.print(f"[yellow]WARNING: Claude CLI 실행 중 오류: {e}[/]")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def save_to_chromadb_direct(
    summary: str,
    backup_data: Dict[str, Any],
    config: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    MCP를 통한 ChromaDB 저장

    claude CLI를 subprocess로 호출하여 MCP chromadb 서버를 통해 저장
    Python 클라이언트 직접 접근보다 안정적이고 빠름

    Args:
        summary: 요약 내용
        backup_data: 백업 데이터
        config: 설정

    Returns:
        (성공 여부, 오류 메시지) 튜플. 성공 시 (True, None), 실패 시 (False, "오류 상세")
    """
    metadata = backup_data.get('backup_metadata', {})
    statistics = backup_data.get('statistics', {})

    doc_id = f"context_compact_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Get metadata template from chromadb_integration config
    chromadb_config = config['chromadb_integration']
    collection_name = chromadb_config['collection']
    metadata_template = chromadb_config['metadata_template']

    # Build doc_metadata from template, filling in dynamic values
    doc_metadata = {
        "project": metadata_template.get('project', 'example_project'),
        "subproject": metadata_template.get('subproject', 'core'),
        "type": metadata_template.get('type', 'context_compact'),
        "date": datetime.now().strftime('%Y-%m-%d'),
        "summary": f"컨텍스트 압축 - {statistics.get('total_messages', 0)}개 메시지",
        "tags": metadata_template.get('tags', 'auto-compact, summary'),
        "status": metadata_template.get('status', 'completed'),
        # Additional dynamic fields
        "original_message_count": statistics.get('total_messages', 0),
        "total_tokens": statistics.get('total_tokens', 0),
        "session_id": metadata.get('session_id', ''),
        "git_branch": metadata.get('git_branch', '') or 'unknown',
        "timestamp": metadata.get('timestamp', '')
    }

    try:
        console.print(f"\n[cyan]SAVE[/] MCP를 통해 ChromaDB에 저장 중...")
        console.print(f"   컬렉션: {collection_name}")
        console.print(f"   문서 ID: {doc_id}")

        # MCP config 경로
        project_root = find_project_root()
        if not project_root:
            return False, "프로젝트 루트를 찾을 수 없습니다"

        mcp_config = project_root / ".claude" / "config" / "chromadb-only-mcp-config.json"
        if not mcp_config.exists():
            return False, f"MCP config 파일이 없습니다: {mcp_config}"

        # JSON 데이터 준비
        mcp_request = {
            "collection_name": collection_name,
            "documents": [summary],
            "ids": [doc_id],
            "metadatas": [doc_metadata]
        }

        # claude CLI로 MCP 호출
        cmd = [
            "claude",
            "-p",
            '--model', 'claude-haiku-4-5',
            "--mcp-config", str(mcp_config),
            "--strict-mcp-config",
            "--dangerously-skip-permissions",
            "--output-format", "json",
            f"chromadb에 문서를 추가하세요. chroma_add_documents 도구를 사용하세요: {json.dumps(mcp_request, ensure_ascii=False)}"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False
        )

        if result.returncode != 0:
            error_detail = f"MCP 호출 실패 (exit code: {result.returncode})\nstderr: {result.stderr[:200]}"
            console.print(f"   [yellow]WARNING: {error_detail}[/]")
            return False, error_detail

        # 성공 확인
        try:
            output = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            output = {"raw": result.stdout}

        console.print(f"   [green]OK[/] ChromaDB 저장 완료!")
        console.print(f"   메시지: {statistics.get('total_messages', 0)}개")
        console.print(f"   토큰: {statistics.get('total_tokens', 0):,}")
        console.print(f"   요약 길이: {len(summary)} 문자\n")

        return True, None

    except subprocess.TimeoutExpired:
        error_detail = "MCP 호출 타임아웃 (120초 초과)"
        console.print(f"   [yellow]WARNING: {error_detail}[/]")
        return False, error_detail
    except Exception as e:
        error_detail = f"ChromaDB 저장 실패: {str(e)}"
        console.print(f"   [yellow]WARNING: {error_detail}[/]")
        traceback.print_exc(file=sys.stderr)
        return False, error_detail


def save_summary_to_chromadb(
    summary: str,
    backup_data: Dict[str, Any],
    config: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    요약을 ChromaDB에 저장 (Python 클라이언트 직접 사용)

    레거시 호환성을 위해 유지되는 래퍼 함수

    Args:
        summary: 요약 내용
        backup_data: 백업 데이터
        config: 설정

    Returns:
        (성공 여부, 오류 메시지) 튜플
    """
    return save_to_chromadb_direct(summary, backup_data, config)


def create_pid_file() -> Optional[Path]:
    """
    Create PID file for background process tracking

    Returns:
        Path to PID file or None if failed
    """
    try:
        project_root = find_project_root()
        if project_root:
            pid_file = project_root / ".claude" / "recovery" / "auto-compact.pid"
        else:
            pid_file = Path(".claude/recovery/auto-compact.pid")

        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()), encoding='utf-8')
        return pid_file
    except Exception as e:
        console.print(f"[yellow]⚠ PID 파일 생성 실패: {e}[/yellow]")
        return None


def remove_pid_file() -> None:
    """Remove PID file"""
    try:
        project_root = find_project_root()
        if project_root:
            pid_file = project_root / ".claude" / "recovery" / "auto-compact.pid"
        else:
            pid_file = Path(".claude/recovery/auto-compact.pid")

        if pid_file.exists():
            pid_file.unlink()
    except Exception as e:
        console.print(f"[yellow]⚠ PID 파일 삭제 실패: {e}[/yellow]")


def update_progress_status(
    status: str,
    stage: str,
    progress: int,
    message: str,
    error: Optional[str] = None,
    started_at: Optional[str] = None
) -> None:
    """
    Update progress status file for PostToolUse hook monitoring

    Args:
        status: running|completed|error
        stage: backup|summary|chromadb|cleanup
        progress: 0-100
        message: Current operation description
        error: Error message if status is error
        started_at: ISO timestamp when started (for first call)
    """
    try:
        project_root = find_project_root()
        if project_root:
            status_file = project_root / ".claude" / "recovery" / "compact-status.json"
        else:
            status_file = Path(".claude/recovery/compact-status.json")

        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data to preserve started_at
        existing_started_at = started_at
        if status_file.exists() and not started_at:
            try:
                existing_data = json.loads(status_file.read_text(encoding='utf-8'))
                existing_started_at = existing_data.get('started_at')
            except Exception:
                pass

        status_data = {
            'pid': os.getpid(),
            'status': status,
            'stage': stage,
            'progress': progress,
            'message': message,
            'started_at': existing_started_at or datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat() if status == 'completed' else None,
            'error': error
        }

        status_file.write_text(json.dumps(status_data, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        console.print(f"[yellow]⚠ 진행 상태 업데이트 실패: {e}[/yellow]")


def save_compact_state(
    backup_file: Optional[Path],
    summary: str,
    config: Dict[str, Any],
    backup_data: Optional[Dict[str, Any]] = None
) -> None:
    """압축 상태 저장 (복구용) - 요약 내용 포함"""
    recovery_config = config.get('recovery', {})

    if not recovery_config.get('save_compact_state', True):
        return

    # 프로젝트 루트 기준 복구 경로 사용
    project_root = find_project_root()
    if project_root:
        recovery_file = project_root / ".claude" / "recovery" / "compact-recovery.json"
    else:
        recovery_file = Path(recovery_config['recovery_file'])

    recovery_file.parent.mkdir(parents=True, exist_ok=True)

    state: Dict[str, Any] = {
        'timestamp': datetime.now().isoformat(),
        'backup_file': str(backup_file) if backup_file else None,
        'summary': summary,  # 요약 내용 저장
        'summary_length': len(summary) if summary else 0,
        'collection': config['chromadb_integration']['collection'],
        'auto_compact_triggered': True,  # 자동 압축 발생 마커
        'recovered': False,  # 복구 필요 (초기값)
    }

    # 백업 데이터에서 통계 추가
    if backup_data:
        statistics = backup_data.get('statistics', {})
        state['statistics'] = {
            'total_messages': statistics.get('total_messages', 0),
            'total_tokens': statistics.get('total_tokens', 0),
            'conversation_duration': statistics.get('conversation_duration_seconds', 0)
        }

    with open(recovery_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def create_compact_marker(config: Dict[str, Any]) -> None:
    """압축 마커 생성 (복구 헬퍼가 감지할 수 있도록)"""
    # 프로젝트 루트 기준 복구 경로 사용
    project_root = find_project_root()
    if project_root:
        recovery_file = project_root / ".claude" / "recovery" / "compact-recovery.json"
    else:
        recovery_config = config.get('recovery', {})
        recovery_file = Path(recovery_config.get('recovery_file', '.claude/recovery/compact-recovery.json'))

    recovery_file.parent.mkdir(parents=True, exist_ok=True)

    state = {
        'timestamp': datetime.now().isoformat(),
        'auto_compact_triggered': True,
        'collection': config['chromadb_integration']['collection'],
        'message': '자동 컨텍스트 압축이 발생했습니다. 대화를 요약하고 ChromaDB에 저장하세요.'
    }

    with open(recovery_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def main():
    """메인 함수"""
    # Sentry 초기화
    init_sentry('auto-compact', additional_tags={'hook_type': 'pre_compact'})

    # 로거 초기화
    logger = HookLogger("auto-compact")

    try:
        logger.log_start()

        add_breadcrumb("Hook execution started", category="lifecycle")

        # PID 파일 생성 (백그라운드 프로세스 추적)
        pid_file = create_pid_file()
        if pid_file:
            add_breadcrumb("PID file created", category="progress", data={"pid": os.getpid()})
            logger.log_info("PID 파일 생성", pid=os.getpid(), pid_file=str(pid_file))

        # 초기 상태 업데이트
        start_time = datetime.now().isoformat()
        update_progress_status(
            status="running",
            stage="init",
            progress=0,
            message="컨텍스트 압축 시작",
            started_at=start_time
        )

        # 설정 로드
        config = load_auto_compact_config()
        add_breadcrumb("Config loaded successfully", category="config", data={"collection": config['chromadb_integration']['collection']})

        update_progress_status(
            status="running",
            stage="init",
            progress=10,
            message="설정 로드 완료"
        )

        # stdin에서 대화 내용 읽기 (PreCompact 훅에서 전달됨)
        # Non-blocking read with timeout - 실패해도 계속 진행
        conversation = ""
        try:
            # 5초 타임아웃으로 stdin 대기
            if select.select([sys.stdin], [], [], 5)[0]:
                conversation = sys.stdin.read()
                logger.log_info(
                    "stdin에서 대화 내용 읽기 성공",
                    content_length=len(conversation) if conversation else 0
                )
            else:
                warning_msg = "stdin 읽기 타임아웃 (5초) - 수동 압축이거나 stdin 전달 안됨"
                console.print(f"[yellow]WARNING: {warning_msg}[/]")
                logger.log_error(warning_msg)
        except Exception as e:
            error_msg = f"stdin 읽기 오류: {e}"
            console.print(f"[yellow]WARNING: {error_msg}[/]")
            logger.log_error(error_msg)

        # 백업 파일 생성 (대화 내용이 있으면)
        backup_file = None
        backup_data = None
        if conversation and conversation.strip():
            update_progress_status(
                status="running",
                stage="backup",
                progress=20,
                message="대화 내용 백업 중..."
            )
            add_breadcrumb("Starting backup creation", category="backup", data={"size": len(conversation)})
            # 대화 내용 백업 (조용히)
            backup_file, backup_data = backup_conversation(conversation, config)
            if backup_file:
                stats = backup_data.get('statistics', {}) if backup_data else {}
                add_breadcrumb("Backup created successfully", category="backup", data={
                    "file": str(backup_file),
                    "messages": stats.get('total_messages', 0),
                    "tokens": stats.get('total_tokens', 0)
                })
                logger.log_info(
                    "백업 파일 생성 완료",
                    backup_file=str(backup_file),
                    total_messages=stats.get('total_messages', 0),
                    total_tokens=stats.get('total_tokens', 0)
                )
                update_progress_status(
                    status="running",
                    stage="backup",
                    progress=40,
                    message=f"백업 완료 ({stats.get('total_messages', 0)}개 메시지)"
                )
        else:
            warning_msg = "대화 내용이 전달되지 않음 - 수동 압축이거나 빈 대화"
            add_breadcrumb(warning_msg, category="backup", level="warning")
            logger.log_error(warning_msg)

        # 압축 마커 생성
        create_compact_marker(config)
        add_breadcrumb("Compact marker created", category="marker")
        logger.log_info("압축 마커 생성 완료")

        # 요약 생성 (Claude CLI 사용, 조용히)
        summary = ""
        if backup_data:
            update_progress_status(
                status="running",
                stage="summary",
                progress=50,
                message="Claude CLI로 요약 생성 중..."
            )
            add_breadcrumb("Starting summary generation", category="summary")
            summary = generate_claude_cli_summary(backup_data, config)

            if summary:
                add_breadcrumb("Summary generated successfully", category="summary", data={"length": len(summary)})
                logger.log_info("요약 생성 완료", summary_length=len(summary))
                update_progress_status(
                    status="running",
                    stage="summary",
                    progress=70,
                    message=f"요약 생성 완료 ({len(summary)} 문자)"
                )

                # ChromaDB에 저장 (조용히)
                update_progress_status(
                    status="running",
                    stage="chromadb",
                    progress=80,
                    message="ChromaDB에 저장 중..."
                )
                add_breadcrumb("Saving to ChromaDB", category="chromadb")
                success, error_msg = save_summary_to_chromadb(summary, backup_data, config)

                if success:
                    add_breadcrumb("ChromaDB save successful", category="chromadb")
                    logger.log_info("ChromaDB 저장 완료")
                    update_progress_status(
                        status="running",
                        stage="chromadb",
                        progress=90,
                        message="ChromaDB 저장 완료"
                    )
                else:
                    add_breadcrumb("ChromaDB save failed", category="chromadb", level="error",
                                 data={"error": error_msg})
                    logger.log_error(f"ChromaDB 저장 실패: {error_msg}")

                    # Sentry에 상세 오류 보고
                    capture_exception(
                        Exception(f"ChromaDB save failed: {error_msg}"),
                        context={
                            "error_detail": error_msg,
                            "collection": config['chromadb_integration']['collection'],
                            "summary_length": len(summary),
                            "message_count": backup_data.get('statistics', {}).get('total_messages', 0)
                        }
                    )
            else:
                add_breadcrumb("Summary generation failed", category="summary", level="error")
                logger.log_error("요약 생성 실패")
        else:
            logger.log_error("백업 데이터 없음")

        # 요약 생성 완료 (백업 파일이 있으면 상태 저장)
        if backup_file:
            update_progress_status(
                status="running",
                stage="cleanup",
                progress=95,
                message="압축 상태 저장 중..."
            )
            save_compact_state(backup_file, summary, config, backup_data)
            add_breadcrumb("Compact state saved", category="state")
            logger.log_info("압축 상태 저장 완료")

        # 완료 상태 업데이트
        update_progress_status(
            status="completed",
            stage="cleanup",
            progress=100,
            message="컨텍스트 압축 완료"
        )

        # PID 파일 삭제
        remove_pid_file()
        add_breadcrumb("PID file removed", category="progress")
        logger.log_info("PID 파일 삭제 완료")

        # 종료
        logger.log_end(
            success=True,
            backup_created=bool(backup_file),
            summary_generated=bool(summary)
        )

        # Sentry flush before exit
        flush()
        sys.exit(0)

    except Exception as e:
        error_msg = f"오류 발생: {e}"
        console.print(f"[red]ERROR: {error_msg}[/]")
        traceback.print_exc(file=sys.stderr)

        # 에러 상태 업데이트
        update_progress_status(
            status="error",
            stage="error",
            progress=0,
            message="컨텍스트 압축 실패",
            error=error_msg
        )

        # PID 파일 삭제
        remove_pid_file()

        # Capture exception to Sentry
        capture_exception(e, context={
            "hook": "auto-compact",
            "error_message": error_msg
        })

        logger.log_end(success=False, error=str(e))

        # Flush Sentry before exit
        flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
