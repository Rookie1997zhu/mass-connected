"""Local filesystem helpers for FieldFile when default storage may be remote (OSS)."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def _copy_field_to_path(field_file, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with field_file.open("rb") as src, open(dest, "wb") as dst:
        shutil.copyfileobj(src, dst)


def materialize_field_file(field_file) -> str:
    """
    Return a local filesystem path for field_file.

    Local storage: uses FieldFile.path.
    Remote (OSS): copies under MEDIA_ROOT/tmp/oss_local for shared-volume Celery access.
    """
    if not field_file:
        raise ValueError("field_file is empty")
    try:
        return field_file.path
    except (NotImplementedError, AttributeError, ValueError):
        pass

    name = field_file.name or "file.bin"
    key = hashlib.sha256(name.encode("utf-8")).hexdigest()[:32]
    suffix = Path(name).suffix or ".bin"
    dest = Path(settings.MEDIA_ROOT) / "tmp" / "oss_local" / f"{key}{suffix}"
    if not dest.is_file():
        logger.debug("materialize remote file name=%s dest=%s", name, dest)
        _copy_field_to_path(field_file, dest)
    return str(dest)


@contextmanager
def local_file_path(field_file):
    """
    Yield a local path for reading field_file; remote copies use a temp file cleaned up on exit.
    """
    if not field_file:
        yield None
        return

    try:
        yield field_file.path
        return
    except (NotImplementedError, AttributeError, ValueError):
        pass

    suffix = Path(field_file.name or "file.bin").suffix or ".bin"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        _copy_field_to_path(field_file, Path(tmp_path))
        yield tmp_path
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            logger.warning("failed to remove temp file path=%s", tmp_path)
