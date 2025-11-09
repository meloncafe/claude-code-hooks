"""Project root detection utilities."""
import os
from pathlib import Path
from typing import Optional


def find_project_root() -> Optional[Path]:
    """
    Find project root by looking for .claude directory.

    Returns:
        Path to project root or None if not found
    """
    current = Path.cwd()

    # Check current directory
    if (current / ".claude").is_dir():
        return current

    # Check parent directories
    for parent in current.parents:
        if (parent / ".claude").is_dir():
            return parent

    return None


def is_project_root() -> bool:
    """Check if current directory is project root."""
    return (Path.cwd() / ".claude").is_dir()


def ensure_project_root() -> bool:
    """
    Ensure current directory is project root.
    Changes directory if needed.

    Returns:
        True if at project root, False if project root not found
    """
    if is_project_root():
        return True

    root = find_project_root()
    if root:
        os.chdir(root)
        return True

    return False
