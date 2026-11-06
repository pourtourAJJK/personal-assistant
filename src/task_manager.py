"""task_manager.py — Business logic layer (AD-2, AD-4, AD-5, AD-6, AD-7).

All public functions return result tuples `(success: bool, message: str, data)`
exactly as pinned in ARCHITECTURE-SPINE.md Rev-2 / Interface Contracts.
Exceptions:

    get_task(task_id) -> dict | None   (per contract)
    generate_task_id(tasks) -> str     (per contract)

AD-4 (write-through, no cache): every operation calls storage.load_tasks()
fresh and — for mutations — storage.save_tasks() immediately after modifying
the list. No module-level task state exists in this module.

AD-6 (message ownership): this module owns operation-result messages (the
PRD's fixed outcome strings). It never prints. storage exceptions are caught
here and converted to failure tuples; cli never sees raw exceptions.
"""

import datetime

import storage

# Operation-result message for a corrupt data file (PRD FR-3 wording).
# Applies to every operation on a corrupt file (AD-7: all fail closed).
_CORRUPTION_MESSAGE = (
    "Data file is corrupted, unable to read tasks. Please check data/tasks.json."
)

# Defensive-validation failure message (AD-2 second stage; cli's re-prompt
# normally prevents reaching this, per the AD-2 validation split).
_INVALID_TASK_MESSAGE = (
    "Invalid task data, please check title, category and due date."
)

# Operation-result message when the data file cannot be accessed (AD-6:
# PermissionError/OSError from storage are converted to a result tuple,
# never propagated to cli). [Wave-5 fix: gap found by S-402 tests.]
_ACCESS_ERROR_MESSAGE = (
    "Unable to access the data file, please check permissions "
    "for data/tasks.json."
)


def _load_or_fail():
    """load_tasks() fresh from disk, converting storage errors to failures.

    Returns (tasks, None) on success; (None, _CORRUPTION_MESSAGE) when the
    file is corrupt (AD-7); (None, _ACCESS_ERROR_MESSAGE) on OSError such as
    PermissionError (AD-6). json.JSONDecodeError is a subclass of ValueError,
    so ValueError covers both corruption signals storage can raise.
    """
    try:
        return storage.load_tasks(), None
    except ValueError:
        return None, _CORRUPTION_MESSAGE
    except OSError:
        return None, _ACCESS_ERROR_MESSAGE


def _save_or_fail(tasks):
    """save_tasks() with the AD-6 boundary applied.

    Returns None on success or _ACCESS_ERROR_MESSAGE on OSError. On failure
    the on-disk file is untouched (atomic write, AD-3) and the caller
    returns a failure tuple; the in-memory mutation is discarded (AD-4
    means no cache, so nothing stale survives).
    """
    try:
        storage.save_tasks(tasks)
        return None
    except OSError:
        return _ACCESS_ERROR_MESSAGE


def _is_task_with_id(task, task_id):
    """True when task is a dict whose id matches exactly."""
    return isinstance(task, dict) and task.get("id") == task_id


# ---------------------------------------------------------------------------
# S-201: ID generation and Task entity construction (AD-2, AD-5)
# ---------------------------------------------------------------------------

def generate_task_id(tasks: list) -> str:
    """Generate the next Task ID: TASK + max(existing numeric suffix) + 1.

    Zero-padded to AT LEAST 3 digits (TASK001); beyond 999 the number grows
    naturally (TASK1000). IDs are never reused after deletion. Records with
    a missing, malformed, or non-string id are skipped, as are non-dict
    entries — they never crash generation and never count toward max.
    """
    max_num = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.startswith("TASK"):
            continue
        suffix = task_id[len("TASK"):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return "TASK" + str(max_num + 1).zfill(3)


def _build_task(title, category, due_date, task_id):
    """Construct a Task dict defensively (AD-2 second validation stage).

    Returns the Task dict, or None when the constructed entity would be
    invalid (caller converts to a failure tuple without saving).
    """
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(category, str) or not category.strip():
        return None
    try:
        datetime.datetime.strptime(due_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
    # created_at pinned to seconds precision — never isoformat() (AD-2).
    return {
        "id": task_id,
        "title": title,
        "category": category,
        "due_date": due_date,
        "completed": False,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# S-202: add_task (FR-1 / FR-2 business side)
# ---------------------------------------------------------------------------

def add_task(title: str, category: str, due_date: str) -> tuple:
    """Create a task: load fresh -> generate ID -> build entity -> save now.

    Returns (True, "Task created successfully! Task ID: {id}, Task title:
    {title}", new_id) or a failure tuple. On a corrupt file: fails closed and
    never saves (AD-7). On an invalid entity: fails without saving (AD-2).
    On an inaccessible file: fails without saving (AD-6).
    """
    tasks, err = _load_or_fail()
    if err:
        return (False, err, None)
    new_id = generate_task_id(tasks)
    task = _build_task(title, category, due_date, new_id)
    if task is None:
        return (False, _INVALID_TASK_MESSAGE, None)
    tasks.append(task)
    save_err = _save_or_fail(tasks)
    if save_err:
        return (False, save_err, None)
    return (True, "Task created successfully! "
                  "Task ID: {}, Task title: {}".format(new_id, title), new_id)


# ---------------------------------------------------------------------------
# S-203: view_tasks + get_task (FR-3 business side; data source for FR-5
# delete confirmation)
# ---------------------------------------------------------------------------

def view_tasks() -> tuple:
    """Read all tasks fresh from disk (no cache, AD-4).

    Returns (True, "", tasks_list) — empty message because cli renders the
    list itself (AD-6); empty/missing file yields (True, "", []).
    """
    tasks, err = _load_or_fail()
    if err:
        return (False, err, None)
    return (True, "", tasks)


def get_task(task_id: str):
    """Return the first task dict whose id matches, or None (per contract).

    Corruption also yields None (the contract has no exception path);
    write-path second-layer protection still guards corruption via the
    result tuples of complete_task/delete_task.
    """
    tasks, err = _load_or_fail()
    if err:
        return None
    for task in tasks:
        if _is_task_with_id(task, task_id):
            return task
    return None


# ---------------------------------------------------------------------------
# S-204: get_statistics (FR-6 business side)
# ---------------------------------------------------------------------------

def get_statistics() -> tuple:
    """Compute counts fresh from disk (AD-4: never cached, PRD FR-6).

    Returns (True, "", {"total": int, "pending": int, "completed": int,
    "completion_rate": int}) with rate 0-100; all zeros when no tasks exist
    (no division by zero). The "%" formatting is cli's display concern.
    """
    tasks, err = _load_or_fail()
    if err:
        return (False, err, None)
    total = len(tasks)
    completed = sum(1 for t in tasks if isinstance(t, dict)
                    and t.get("completed") is True)
    pending = total - completed
    rate = round(completed * 100 / total) if total else 0
    return (True, "", {"total": total, "pending": pending,
                       "completed": completed, "completion_rate": rate})


# ---------------------------------------------------------------------------
# S-205: complete_task (FR-4 business side)
# ---------------------------------------------------------------------------

def complete_task(task_id: str) -> tuple:
    """Mark a task completed: load fresh -> flip bool -> save immediately.

    Returns (True, "Task {id} marked as complete!", None) on success;
    (True, "Task {id} is already completed.", None) for the idempotent
    no-op [pinned in the spine contract]; (False, "Task not found, please
    check the Task ID.", None) when the ID does not exist. On a corrupt
    file: fails closed, never saves (AD-7). On an inaccessible file:
    fails without saving (AD-6).
    """
    tasks, err = _load_or_fail()
    if err:
        return (False, err, None)
    for task in tasks:
        if _is_task_with_id(task, task_id):
            if task.get("completed") is True:
                return (True, "Task {} is already completed.".format(task_id),
                        None)
            task["completed"] = True
            save_err = _save_or_fail(tasks)
            if save_err:
                return (False, save_err, None)
            return (True, "Task {} marked as complete!".format(task_id), None)
    return (False, "Task not found, please check the Task ID.", None)


# ---------------------------------------------------------------------------
# S-206: delete_task (FR-5 business side)
# ---------------------------------------------------------------------------

def delete_task(task_id: str) -> tuple:
    """Remove a task: load fresh -> remove exactly one match -> save now.

    Returns (True, "Task {id} deleted successfully!", None) or
    (False, "Task not found.", None) — note the shorter PRD FR-5 wording,
    distinct from FR-4's message. ID non-reuse is guaranteed by
    generate_task_id (AD-5), not here. On a corrupt file: fails closed,
    never saves (AD-7). On an inaccessible file: fails without saving (AD-6).
    """
    tasks, err = _load_or_fail()
    if err:
        return (False, err, None)
    for index, task in enumerate(tasks):
        if _is_task_with_id(task, task_id):
            del tasks[index]
            save_err = _save_or_fail(tasks)
            if save_err:
                return (False, save_err, None)
            return (True, "Task {} deleted successfully!".format(task_id),
                    None)
    return (False, "Task not found.", None)
