"""storage.py — Data access layer (AD-3, AD-7).

Sole owner of all reads and writes to data/tasks.json. No other module may
import json for task data or reference the data file path (AD-3).

Public contract (ARCHITECTURE-SPINE.md Rev-2, Interface Contracts):
    load_tasks()  -> list    # [] if missing/empty; raises on corrupt file
    save_tasks(tasks: list) -> None  # atomic write; creates data/ dir if missing

Corruption definition (AD-7): a NON-EMPTY file that either fails json.loads,
or parses to a root that is not a JSON array. Corrupt files are never
repaired, reset, or overwritten by this module.
"""

import json
import os
import tempfile

# Path base decision [USER-APPROVED 2026-11-06]: resolved from this file's
# location — project root is the parent of src/. data/tasks.json therefore
# always lives at <project_root>/data/tasks.json regardless of the CWD the
# program is launched from. Implementation detail only; the public function
# signatures above are unchanged.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")


def load_tasks() -> list:
    """Read all tasks from data/tasks.json.

    Returns:
        list[dict]: the task array stored in the file.
        [] when the file or its directory does not exist (FR-3/FR-7:
        no crash), or when the file is empty/whitespace-only (empty,
        not corrupt — AD-3).

    Raises:
        json.JSONDecodeError: file is non-empty but is not valid JSON
            (corruption signal, AD-7). The file is never modified here.
        ValueError: file is valid JSON but the root is not an array
            (corruption signal, AD-7). The file is never modified here.
    """
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    if content.strip() == "":
        return []  # 0-byte (or blank) file: empty, not corrupt
    tasks = json.loads(content)  # json.JSONDecodeError propagates on corruption
    if not isinstance(tasks, list):
        raise ValueError("Data file root is not a JSON array.")
    return tasks


def save_tasks(tasks: list) -> None:
    """Persist the full task array to data/tasks.json (atomic write, AD-3).

    Creates the data/ directory if missing (lazy initialization — the
    [USER-APPROVED] resolution of PRD FR-7 vs AD-3: the directory is created
    on first save, not on startup).

    The write is atomic: JSON is dumped to a temporary file in the same
    directory, then os.replace()d over the target. The target file is never
    partially written and is preserved unchanged if any step fails.

    Args:
        tasks: the complete task array to persist (list of Task dicts).

    Raises:
        Propagates OSError (including PermissionError, AD-6) if the write
        cannot be completed; the original file is left untouched.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, DATA_FILE)
    finally:
        # After a successful os.replace the temp path no longer exists;
        # on any failure this removes the partial temp file so the target
        # keeps its previous content (AD-3 atomicity guarantee).
        if os.path.exists(temp_path):
            os.remove(temp_path)
