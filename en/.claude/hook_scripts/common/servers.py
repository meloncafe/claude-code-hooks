#!/usr/bin/env python3
"""
Server management utilities for Example Project project.

Handles:
- Starting/stopping backend and frontend servers
- PID file management
- Process validation
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

app = typer.Typer(help="Server Management Utilities")
console = Console()

# PID files and ports per server type
SERVER_CONFIG = {
    "backend": {
        "main": {
            "pid_file": Path("/tmp/backend-main.pid"),
            "port": 8000,
            "app_path": "example_project.main:app"
        },
        "auth": {
            "pid_file": Path("/tmp/backend-auth.pid"),
            "port": 8001,
            "app_path": "example_project_auth.api.app:app"
        },
        "auth-example": {
            "pid_file": Path("/tmp/backend-auth-example.pid"),
            "port": 8002,
            "app_path": "auth_backend.__main__:app"
        }
    },
    "frontend": {
        "auth-example": {
            "pid_file": Path("/tmp/frontend-auth-example.pid"),
            "port": 5173,
        }
    }
}

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_PATHS = {
    "main": PROJECT_ROOT,
    "auth-example": PROJECT_ROOT / "packages" / "example_module" / "examples" / "auth-backend",
}
FRONTEND_PATHS = {
    "auth-example": PROJECT_ROOT / "packages" / "example_module" / "examples" / "auth-frontend",
}


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def get_pid_from_port(port: int) -> Optional[int]:
    """Get PID of process listening on given port."""
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split('\n')[0])
        return None
    except (subprocess.TimeoutExpired, ValueError, subprocess.SubprocessError):
        return None


def read_pid_file(pid_file: Path) -> Optional[int]:
    """Read PID from file and validate it."""
    if not pid_file.exists():
        return None

    try:
        content = pid_file.read_text().strip()
        if not content:
            return None

        pid = int(content)

        if is_process_running(pid):
            return pid
        else:
            pid_file.unlink()
            return None
    except (ValueError, OSError):
        if pid_file.exists():
            pid_file.unlink()
        return None


def write_pid_file(pid_file: Path, pid: int) -> bool:
    """Write PID to file."""
    try:
        pid_file.write_text(str(pid))
        return True
    except OSError:
        return False


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill process with given PID."""
    try:
        signal = 9 if force else 15
        os.kill(pid, signal)

        for _ in range(10):
            if not is_process_running(pid):
                return True
            time.sleep(0.5)

        if not force and is_process_running(pid):
            return kill_process(pid, force=True)

        return not is_process_running(pid)
    except (OSError, ValueError):
        return False


def stop_server_internal(server_category: str, server_type: str) -> Tuple[bool, str]:
    """Internal function to stop backend or frontend server.

    Args:
        server_category: 'backend' or 'frontend'
        server_type: Type like 'main', 'auth', 'auth-example'
    """
    if server_category not in SERVER_CONFIG:
        return False, f"Invalid server category: {server_category}"

    if server_type not in SERVER_CONFIG[server_category]:
        return False, f"Invalid {server_category} type: {server_type}"

    config = SERVER_CONFIG[server_category][server_type]
    pid_file = config["pid_file"]
    port = config["port"]
    name = f"{server_category.capitalize()} ({server_type})"

    pid = read_pid_file(pid_file)

    if pid is None:
        pid = get_pid_from_port(port)

    if pid is None:
        if pid_file.exists():
            pid_file.unlink()
        return True, f"{name} server is not running"

    if kill_process(pid):
        if pid_file.exists():
            pid_file.unlink()
        return True, f"{name} server stopped (PID: {pid})"
    else:
        return False, f"Failed to stop {name} server (PID: {pid})"


def start_frontend_server_internal(
    frontend_type: str,
    clean_cache: bool = False,
    wait_for_start: int = 3
) -> Tuple[bool, str, Optional[int]]:
    """Internal function to start frontend development server.

    Args:
        frontend_type: Frontend type like 'auth-example'
        clean_cache: Whether to clean Vite cache
        wait_for_start: Seconds to wait for server startup
    """
    if frontend_type not in SERVER_CONFIG["frontend"]:
        return False, f"Invalid frontend type: {frontend_type}", None

    if frontend_type not in FRONTEND_PATHS:
        return False, f"No path configured for frontend type: {frontend_type}", None

    config = SERVER_CONFIG["frontend"][frontend_type]
    pid_file = config["pid_file"]
    port = config["port"]
    working_dir = FRONTEND_PATHS[frontend_type]

    existing_pid = read_pid_file(pid_file)
    if existing_pid:
        return True, f"Frontend ({frontend_type}) is already running (PID: {existing_pid})", existing_pid

    port_pid = get_pid_from_port(port)
    if port_pid:
        write_pid_file(pid_file, port_pid)
        return True, f"Frontend ({frontend_type}) is already running on port {port} (PID: {port_pid})", port_pid

    if clean_cache:
        cache_dir = working_dir / "node_modules" / ".vite"
        if cache_dir.exists():
            try:
                import shutil
                shutil.rmtree(cache_dir)
            except OSError:
                pass

    try:
        log_file = Path(f"/tmp/frontend-{frontend_type}.log")
        with open(log_file, 'w') as f:
            subprocess.Popen(
                ['yarn', 'dev'],
                cwd=str(working_dir),
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, 'PORT': str(port)}
            )

        time.sleep(wait_for_start)

        pid = get_pid_from_port(port)

        if pid:
            write_pid_file(pid_file, pid)
            return True, f"Frontend ({frontend_type}) started on port {port} (PID: {pid})", pid
        else:
            return False, f"Frontend ({frontend_type}) failed to start - port {port} not listening", None

    except (subprocess.SubprocessError, OSError) as e:
        return False, f"Failed to start frontend ({frontend_type}): {e}", None


def start_backend_server_internal(
    backend_type: str,
    wait_for_start: int = 3
) -> Tuple[bool, str, Optional[int]]:
    """Internal function to start backend development server.

    Args:
        backend_type: Backend type like 'main', 'auth', 'auth-example'
        wait_for_start: Seconds to wait for server startup
    """
    if backend_type not in SERVER_CONFIG["backend"]:
        return False, f"Invalid backend type: {backend_type}", None

    if backend_type not in BACKEND_PATHS:
        return False, f"No path configured for backend type: {backend_type}", None

    config = SERVER_CONFIG["backend"][backend_type]
    pid_file = config["pid_file"]
    port = config["port"]
    app_path = config["app_path"]
    working_dir = BACKEND_PATHS[backend_type]

    existing_pid = read_pid_file(pid_file)
    if existing_pid:
        return True, f"Backend ({backend_type}) is already running (PID: {existing_pid})", existing_pid

    port_pid = get_pid_from_port(port)
    if port_pid:
        write_pid_file(pid_file, port_pid)
        return True, f"Backend ({backend_type}) is already running on port {port} (PID: {port_pid})", port_pid

    try:
        log_file = Path(f"/tmp/backend-{backend_type}.log")
        with open(log_file, 'w') as f:
            subprocess.Popen(
                ['poetry', 'run', 'uvicorn', app_path, '--reload', '--port', str(port)],
                cwd=str(working_dir),
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )

        time.sleep(wait_for_start)

        pid = get_pid_from_port(port)

        if pid:
            write_pid_file(pid_file, pid)
            return True, f"Backend ({backend_type}) started on port {port} (PID: {pid})", pid
        else:
            return False, f"Backend ({backend_type}) failed to start - port {port} not listening", None

    except (subprocess.SubprocessError, OSError) as e:
        return False, f"Failed to start backend ({backend_type}): {e}", None


def get_server_status_internal(server_category: str, server_type: str) -> Tuple[bool, str, Optional[int]]:
    """Internal function to get status of backend or frontend server.

    Args:
        server_category: 'backend' or 'frontend'
        server_type: Type like 'main', 'auth', 'auth-example'
    """
    if server_category not in SERVER_CONFIG:
        return False, f"Invalid server category: {server_category}", None

    if server_type not in SERVER_CONFIG[server_category]:
        return False, f"Invalid {server_category} type: {server_type}", None

    config = SERVER_CONFIG[server_category][server_type]
    pid_file = config["pid_file"]
    port = config["port"]
    name = f"{server_category.capitalize()} ({server_type})"

    pid = read_pid_file(pid_file)

    if pid:
        return True, f"{name} is running (PID: {pid}, port: {port})", pid

    port_pid = get_pid_from_port(port)

    if port_pid:
        write_pid_file(pid_file, port_pid)
        return True, f"{name} is running on port {port} (PID: {port_pid}, updated PID file)", port_pid

    return False, f"{name} is not running", None


@app.command()
def status(
    server_category: str = typer.Argument(..., help="Server category: backend or frontend"),
    server_type: str = typer.Argument(..., help="Server type (e.g., main, auth, auth-example)")
):
    """Check server status"""
    is_running, message, pid = get_server_status_internal(server_category, server_type)

    if is_running:
        console.print(f"[green]RUNNING[/] {message}", style="bold")
        raise typer.Exit(0)
    else:
        console.print(f"[yellow]STOPPED[/] {message}", style="bold")
        raise typer.Exit(1)


@app.command()
def stop(
    server_category: str = typer.Argument(..., help="Server category: backend or frontend"),
    server_type: str = typer.Argument(..., help="Server type (e.g., main, auth, auth-example)")
):
    """Stop server"""
    with console.status(f"[cyan]Stopping {server_category} ({server_type})..."):
        success, message = stop_server_internal(server_category, server_type)

    if success:
        console.print(f"[green]SUCCESS[/] {message}", style="bold")
        raise typer.Exit(0)
    else:
        console.print(f"[red]FAILED[/] {message}", style="bold")
        raise typer.Exit(1)


@app.command()
def start_frontend(
    frontend_type: str = typer.Argument("auth-example", help="Frontend type: auth-example"),
    clean_cache: bool = typer.Option(False, "--clean-cache", help="Clean Vite cache before starting")
):
    """Start frontend development server"""
    if frontend_type not in FRONTEND_PATHS:
        console.print(f"[red]ERROR[/] Unknown frontend type: {frontend_type}", style="bold")
        console.print(f"[yellow]Available types:[/] {', '.join(FRONTEND_PATHS.keys())}")
        raise typer.Exit(1)

    with console.status(f"[cyan]Starting frontend ({frontend_type})..."):
        success, message, pid = start_frontend_server_internal(frontend_type, clean_cache=clean_cache)

    if success:
        config = SERVER_CONFIG["frontend"][frontend_type]
        console.print(f"[green]SUCCESS[/] {message}", style="bold")
        console.print(f"[dim]Log file: /tmp/frontend-{frontend_type}.log[/]")
        console.print(f"[dim]Port: {config['port']}[/]")
        raise typer.Exit(0)
    else:
        console.print(f"[red]FAILED[/] {message}", style="bold")
        raise typer.Exit(1)


@app.command()
def start_backend(
    backend_type: str = typer.Argument("auth-example", help="Backend type: main, auth, or auth-example")
):
    """Start backend development server"""
    if backend_type not in BACKEND_PATHS:
        console.print(f"[red]ERROR[/] Unknown backend type: {backend_type}", style="bold")
        console.print(f"[yellow]Available types:[/] {', '.join(BACKEND_PATHS.keys())}")
        raise typer.Exit(1)

    with console.status(f"[cyan]Starting backend ({backend_type})..."):
        success, message, pid = start_backend_server_internal(backend_type)

    if success:
        config = SERVER_CONFIG["backend"][backend_type]
        console.print(f"[green]SUCCESS[/] {message}", style="bold")
        console.print(f"[dim]Log file: /tmp/backend-{backend_type}.log[/]")
        console.print(f"[dim]Port: {config['port']}[/]")
        raise typer.Exit(0)
    else:
        console.print(f"[red]FAILED[/] {message}", style="bold")
        raise typer.Exit(1)


@app.command()
def list():
    """Show status of all servers"""
    table = Table(title="SERVER STATUS", show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Port", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("PID", justify="right")

    # Backend servers
    for backend_type, config in SERVER_CONFIG["backend"].items():
        is_running, _, pid = get_server_status_internal("backend", backend_type)
        status = "[green]RUNNING[/]" if is_running else "[yellow]STOPPED[/]"
        pid_str = str(pid) if pid else "-"
        table.add_row("Backend", backend_type, str(config["port"]), status, pid_str)

    # Frontend servers
    for frontend_type, config in SERVER_CONFIG["frontend"].items():
        is_running, _, pid = get_server_status_internal("frontend", frontend_type)
        status = "[green]RUNNING[/]" if is_running else "[yellow]STOPPED[/]"
        pid_str = str(pid) if pid else "-"
        table.add_row("Frontend", frontend_type, str(config["port"]), status, pid_str)

    console.print(table)


@app.command()
def stop_all():
    """Stop all running servers"""
    stopped_count = 0
    failed_count = 0
    results = []

    console.print("\n[cyan]Stopping all servers...[/cyan]\n")

    # Stop all backend servers
    for backend_type in SERVER_CONFIG["backend"].keys():
        is_running, _, _ = get_server_status_internal("backend", backend_type)
        if is_running:
            success, message = stop_server_internal("backend", backend_type)
            results.append((f"Backend ({backend_type})", success, message))
            if success:
                stopped_count += 1
            else:
                failed_count += 1

    # Stop all frontend servers
    for frontend_type in SERVER_CONFIG["frontend"].keys():
        is_running, _, _ = get_server_status_internal("frontend", frontend_type)
        if is_running:
            success, message = stop_server_internal("frontend", frontend_type)
            results.append((f"Frontend ({frontend_type})", success, message))
            if success:
                stopped_count += 1
            else:
                failed_count += 1

    # Print results
    for name, success, message in results:
        if success:
            console.print(f"[green]✓[/] {name}: {message}")
        else:
            console.print(f"[red]✗[/] {name}: {message}")

    # Summary
    console.print(f"\n[bold]Summary:[/] Stopped: {stopped_count}, Failed: {failed_count}")

    if failed_count > 0:
        raise typer.Exit(1)
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
