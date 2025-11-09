#!/usr/bin/env python3
"""
Example Project Session Start Script

At session start, execute the following in order:
1. Clear terminal screen - Delete scrollback and prevent screen flickering
2. Context Recovery Helper - Check if starting after automatic compacting
3. Pre-Session Hook - Display project information and task guide

Usage:
    python .claude/session-start.py
"""

import os
import subprocess
import sys
from pathlib import Path

from common.logger import HookLogger, rotate_logs
from common.formatting import console, print_rule


def get_script_dir() -> Path:
    """Return the directory where the script is located"""
    return Path(__file__).parent


def run_script(script_name: str, description: str, logger=None) -> bool:
    """
    Script Execution

    Args:
        script_name: Name of the script to execute
        description: Script description
        logger: HookLogger instance (optional)

    Returns:
        Success status
    """
    script_dir = get_script_dir()
    script_path = script_dir / script_name

    if logger:
        logger.log_info(f"Start script execution", script=script_name, description=description)

    if not script_path.exists():
        error_msg = f"{script_name} cannot be found.: {script_path}"
        console.print(f"[yellow][WARNING] {error_msg}[/yellow]")
        if logger:
            logger.log_error(error_msg, script=script_name)
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print(result.stdout, end='', flush=True)

        if result.stderr:
            print(result.stderr, end='', file=sys.stderr, flush=True)

        if result.returncode != 0:
            error_msg = f"Error occurred while executing {script_name} (proceeding)"
            console.print(f"\n[yellow][WARNING] {error_msg}[/yellow]")
            if logger:
                logger.log_error(error_msg, script=script_name, returncode=result.returncode)
        else:
            if logger:
                logger.log_info(f"Script execution complete", script=script_name, returncode=result.returncode)

        return True

    except Exception as e:
        error_msg = f"{script_name} execution failed: {e}"
        console.print(f"[red][ERROR] {error_msg}[/red]")
        if logger:
            logger.log_error(error_msg, script=script_name, exception=str(e))
        return False


def main():
    """Main Function"""
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
            "Step 1: Context Recovery Verification",
            logger
        )

        # 2. Pre-Session Hook 실행
        run_script(
            "pre_session_hook.py",
            "Step 2: Project Information and Work Guide",
            logger
        )

        if logger:
            logger.log_end(success=True)

        sys.exit(0)

    except Exception as e:
        if logger:
            logger.log_end(success=False, error=str(e))
        raise


if __name__ == "__main__":
    main()
