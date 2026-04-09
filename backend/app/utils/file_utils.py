"""
utils/file_utils.py - Safe file reading and writing helpers.
"""

import os
import shutil
from datetime import datetime
from typing import Optional

from app.core.logger import logger


def read_file(path: str) -> str:
    """Read a text file, raising FileNotFoundError if missing."""
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    logger.info("read %d chars from %s", len(content), abs_path)
    return content


def write_file(path: str, content: str) -> str:
    """Write content to path, creating parent dirs as needed. Returns abs path."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    logger.info("wrote %d chars to %s", len(content), abs_path)
    return abs_path


def backup_file(src: str, backup_dir: str) -> Optional[str]:
    """Copy src into backup_dir with a timestamp. Returns backup path or None."""
    if not os.path.isfile(src):
        return None
    os.makedirs(backup_dir, exist_ok=True)
    name = os.path.basename(src)
    stem, ext = os.path.splitext(name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(backup_dir, f"{stem}_{ts}{ext}")
    shutil.copy2(src, dst)
    logger.info("backed up %s -> %s", src, dst)
    return dst
