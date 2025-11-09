#!/usr/bin/env python3
"""
Hook Logs Viewer - 훅 스크립트 로그 조회 및 분석

컨텍스트 효율적인 로그 분석 도구
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import box

app = typer.Typer(help="Hook Logs Viewer - 훅 스크립트 로그 조회 및 분석")
console = Console()


def find_log_dir() -> Optional[Path]:
    """로그 디렉토리 찾기"""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        log_dir = parent / ".claude" / "logs" / "hooks"
        if log_dir.exists():
            return log_dir
    return None


def read_logs(script_name: str, limit: int = 20) -> List[Dict[str, Any]]:
    """로그 파일에서 최신 N개 로그 읽기"""
    log_dir = find_log_dir()
    if not log_dir:
        return []

    log_file = log_dir / f"{script_name}.log"
    if not log_file.exists():
        return []

    logs = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

    return logs


def format_timestamp(ts: str) -> str:
    """타임스탬프를 읽기 쉬운 형식으로 변환"""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%m-%d %H:%M:%S')
    except Exception:
        return ts


def analyze_logs(script_name: str, limit: int = 20, errors_only: bool = False) -> Dict[str, Any]:
    """로그 분석 및 요약"""
    logs = read_logs(script_name, limit)

    if not logs:
        return {
            "status": "no_logs",
            "script": script_name,
            "message": f"{script_name} 로그 파일이 없거나 비어있습니다."
        }

    total_runs = sum(1 for log in logs if log.get('event') == 'start')
    successful_runs = sum(1 for log in logs if log.get('event') == 'end' and log.get('success'))
    failed_runs = sum(1 for log in logs if log.get('event') == 'end' and not log.get('success'))
    errors = [log for log in logs if log.get('event') == 'error']

    recent_runs = []
    for i, log in enumerate(logs):
        if log.get('event') == 'start':
            start_log = log
            end_log = None
            for j in range(i + 1, len(logs)):
                if logs[j].get('event') == 'end':
                    end_log = logs[j]
                    break

            run_info = {
                "timestamp": format_timestamp(start_log.get('timestamp', '')),
                "success": end_log.get('success') if end_log else None,
                "duration": end_log.get('duration_seconds') if end_log else None,
            }

            if end_log:
                for key, value in end_log.items():
                    if key not in ['timestamp', 'event', 'script', 'success', 'duration_seconds']:
                        run_info[key] = value

            recent_runs.append(run_info)

    if errors_only:
        return {
            "status": "errors",
            "script": script_name,
            "total_errors": len(errors),
            "errors": [
                {
                    "timestamp": format_timestamp(err.get('timestamp', '')),
                    "error": err.get('error', err.get('message', 'Unknown error'))
                }
                for err in errors
            ]
        }

    return {
        "status": "ok",
        "script": script_name,
        "statistics": {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "error_count": len(errors)
        },
        "recent_runs": recent_runs[-5:],
        "errors": [
            {
                "timestamp": format_timestamp(err.get('timestamp', '')),
                "error": err.get('error', err.get('message', 'Unknown error'))
            }
            for err in errors[-3:]
        ] if errors else []
    }


def get_all_scripts() -> List[str]:
    """사용 가능한 모든 스크립트 목록"""
    log_dir = find_log_dir()
    if not log_dir:
        return []

    scripts = []
    for log_file in log_dir.glob("*.log"):
        scripts.append(log_file.stem)
    return sorted(scripts)


@app.command()
def view(
    script: Optional[str] = typer.Argument(None, help="스크립트 이름 (예: session_start)"),
    limit: int = typer.Option(20, "--limit", "-n", help="조회할 로그 개수"),
    errors: bool = typer.Option(False, "--errors", "-e", help="에러만 표시"),
    json_output: bool = typer.Option(False, "--json", help="JSON 형식으로 출력"),
):
    """훅 스크립트 로그 조회"""

    if not script:
        console.print("[yellow]WARNING[/] 스크립트 이름을 지정하세요.", style="bold")
        console.print("\n예시: [cyan]python view_logs.py session_start[/]")
        console.print("또는: [cyan]python view_logs.py --list[/]")
        raise typer.Exit(1)

    result = analyze_logs(script, limit, errors)

    if json_output:
        console.print(Syntax(json.dumps(result, indent=2, ensure_ascii=False), "json"))
        return

    console.print(Panel(f"LOG ANALYSIS: {result['script']}", style="cyan bold", box=box.DOUBLE))
    console.print()

    if result['status'] == 'no_logs':
        console.print(f"[yellow]WARNING[/] {result['message']}", style="bold")
        return

    if result['status'] == 'errors':
        console.print(f"[red]ERROR[/] 총 {result['total_errors']}개 에러", style="bold")
        console.print()

        error_table = Table(show_header=True, header_style="bold red", box=box.ROUNDED)
        error_table.add_column("시간", style="cyan")
        error_table.add_column("에러", style="red")

        for err in result['errors']:
            error_table.add_row(err['timestamp'], err['error'])

        console.print(error_table)
        return

    stats = result['statistics']

    stats_table = Table(show_header=False, box=box.SIMPLE)
    stats_table.add_column("항목", style="cyan bold")
    stats_table.add_column("값", style="white")

    stats_table.add_row("총 실행", f"{stats['total_runs']}회")
    stats_table.add_row("성공", f"[green]{stats['successful_runs']}회[/]")
    stats_table.add_row("실패", f"[red]{stats['failed_runs']}회[/]")
    stats_table.add_row("에러", f"[yellow]{stats['error_count']}개[/]")

    console.print(Panel(stats_table, title="STATISTICS", border_style="cyan"))
    console.print()

    if result['recent_runs']:
        runs_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        runs_table.add_column("상태", justify="center", style="bold")
        runs_table.add_column("시간", style="cyan")
        runs_table.add_column("소요시간", justify="right")
        runs_table.add_column("추가 정보", style="dim")

        for run in result['recent_runs']:
            if run.get('success'):
                status = "[green]OK[/]"
            elif run.get('success') is False:
                status = "[red]FAIL[/]"
            else:
                status = "[yellow]RUN[/]"

            duration = f"{run['duration']:.3f}s" if run.get('duration') else "N/A"

            extra_info = []
            for key, value in run.items():
                if key not in ['timestamp', 'success', 'duration']:
                    extra_info.append(f"{key}: {value}")
            extra_str = ", ".join(extra_info) if extra_info else "-"

            runs_table.add_row(status, run['timestamp'], duration, extra_str)

        console.print(Panel(runs_table, title="RECENT RUNS", border_style="cyan"))
        console.print()

    if result['errors']:
        console.print("[red bold]RECENT ERRORS:[/]")
        for err in result['errors']:
            console.print(Panel(
                f"[red]{err['error']}[/]",
                title=f"[red]{err['timestamp']}[/]",
                border_style="red"
            ))
        console.print()


@app.command("list")
def list_scripts():
    """사용 가능한 스크립트 목록 표시"""
    scripts = get_all_scripts()

    if not scripts:
        console.print("[yellow]WARNING[/] 로그 파일이 없습니다.", style="bold")
        return

    table = Table(title="AVAILABLE SCRIPTS", show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("번호", justify="right", style="dim")
    table.add_column("스크립트", style="cyan")

    for idx, script in enumerate(scripts, 1):
        table.add_row(str(idx), script)

    console.print(table)


if __name__ == "__main__":
    app()
