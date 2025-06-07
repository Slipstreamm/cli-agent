import os
import shutil


def restore_backups(search_dir: str = ".", extension: str = ".bak") -> None:
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
    for root, _, files in os.walk(search_dir):
        for filename in files:
            if not filename.endswith(extension):
                continue
            backup_path = os.path.join(root, filename)
            original_path = os.path.join(root, filename[: -len(extension)])
            try:
                shutil.copy2(backup_path, original_path)
                print(f"Restored {original_path} from {backup_path}")
            except Exception as exc:  # pragma: no cover - best effort restore
                print(f"Failed to restore {original_path} from {backup_path}: {exc}")
