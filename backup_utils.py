import os
import shutil
import logging


LOGGER = logging.getLogger(__name__)


def restore_backups(
    search_dir: str = ".",
    extension: str = ".bak",
    target_root: str | None = None,
) -> None:
    """Restore backups in a directory tree.

    The agent calls this helper at startup before it begins modifying files.
    It walks ``search_dir`` recursively looking for files that end with
    ``extension`` (by default ``.bak``). When it finds ``foo.txt.bak`` it copies
    the backup over ``foo.txt`` so that any previous state is restored.

    Parameters
    ----------
    search_dir:
        Root directory to scan. Defaults to the current working directory.
    extension:
        Backup file extension. Defaults to ``.bak``.
    """
    restore_root = target_root or search_dir

    for root, _, files in os.walk(search_dir):
        for filename in files:
            if not filename.endswith(extension):
                continue
            backup_path = os.path.join(root, filename)
            if restore_root != search_dir:
                rel_path = os.path.relpath(backup_path, search_dir)
                original_path = os.path.join(restore_root, rel_path[: -len(extension)])
            else:
                original_path = os.path.join(root, filename[: -len(extension)])
            try:
                os.makedirs(os.path.dirname(original_path), exist_ok=True)
                shutil.copy2(backup_path, original_path)
                LOGGER.info("Restored %s from %s", original_path, backup_path)
            except Exception as exc:  # pragma: no cover - best effort restore
                LOGGER.warning(
                    "Failed to restore %s from %s: %s",
                    original_path,
                    backup_path,
                    exc,
                )


def create_backup(
    file_path: str,
    extension: str = ".bak",
    backup_dir: str | None = None,
) -> str:
    """Create a backup of ``file_path`` and return the backup path."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, os.path.basename(file_path) + extension)
    else:
        backup_path = file_path + extension

    shutil.copy2(file_path, backup_path)
    LOGGER.info("Created backup %s", backup_path)
    return backup_path
