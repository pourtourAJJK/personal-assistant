"""cli.py — Presentation layer (AD-1, AD-2 validation split, AD-6 message split).

Responsibilities: menu loop, raw-input validation with re-prompt, result
display. This module NEVER imports json, NEVER touches data/tasks.json,
NEVER catches storage exceptions, and NEVER uses a bare except (AD-6).

Message ownership (AD-6, two disjoint sets):
    - cli owns interaction messages: menu text, prompts, re-prompt messages,
      "No tasks recorded yet.", "Delete operation cancelled."
    - task_manager owns operation-result messages: every string returned in
      a result tuple is displayed verbatim, never rewritten here.
"""

import datetime
import re

import task_manager

_MENU = (
    "\n================================\n"
    "  QuickTask - Task Manager\n"
    "================================\n"
    "1. Add Task\n"
    "2. View Tasks\n"
    "3. Complete Task\n"
    "4. Delete Task\n"
    "5. Task Statistics\n"
    "6. Exit\n"
)

# Interaction messages owned by cli (AD-6 cli set).
_MSG_INVALID_OPTION = "Invalid option, please enter a number from 1 to 6."
_MSG_EMPTY_TITLE = "Task title cannot be empty, please re-enter."
_MSG_EMPTY_CATEGORY = "Task category cannot be empty, please re-enter."
_MSG_BAD_DATE_FORMAT = "Invalid date format, please use YYYY-MM-DD."
_MSG_BAD_DATE_VALUE = "Invalid date value, please check the date."
_MSG_NO_TASKS = "No tasks recorded yet."
_MSG_DELETE_CANCELLED = "Delete operation cancelled."
_MSG_CONFIRM_DELETE = "Are you sure you want to delete this task? (y/n)"

_DATE_SHAPE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# S-301: raw-input validation helpers (AD-2 stage 1 — cli validates raw
# input with re-prompt; task_manager re-validates the constructed entity)
# ---------------------------------------------------------------------------

def _prompt_title():
    """Prompt until title is non-empty after trimming whitespace."""
    while True:
        title = input("Enter task title: ").strip()
        if title:
            return title
        print(_MSG_EMPTY_TITLE)


def _prompt_category():
    """Prompt until category is non-empty after trimming whitespace."""
    while True:
        category = input("Enter task category: ").strip()
        if category:
            return category
        print(_MSG_EMPTY_CATEGORY)


def _prompt_due_date():
    """Prompt until due date is a valid YYYY-MM-DD calendar date.

    Two-stage rejection per PRD FR-1: shape errors (e.g. 2026/11/15) get the
    format message; well-shaped but impossible dates (e.g. 2026-13-45) get
    the value message. Past dates are allowed (PRD §9 Q3).
    """
    while True:
        raw = input("Enter due date (YYYY-MM-DD): ").strip()
        if not _DATE_SHAPE_RE.match(raw):
            print(_MSG_BAD_DATE_FORMAT)
            continue
        try:
            datetime.datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            print(_MSG_BAD_DATE_VALUE)
            continue
        return raw


def _prompt_task_id(action):
    """Prompt for a Task ID (trimmed)."""
    return input("Enter the Task ID to {}: ".format(action)).strip()


def _print_result(message):
    """Display an operation-result message verbatim (AD-6: no rewriting)."""
    print(message)


# ---------------------------------------------------------------------------
# S-302: Add Task flow (FR-1)
# ---------------------------------------------------------------------------

def _handle_add():
    title = _prompt_title()
    category = _prompt_category()
    due_date = _prompt_due_date()
    _success, message, _data = task_manager.add_task(title, category, due_date)
    _print_result(message)


# ---------------------------------------------------------------------------
# S-303: View Tasks + Task Statistics flows (FR-3 / FR-6)
# ---------------------------------------------------------------------------

def _render_task(task):
    """Render one task block: one field per line, PRD FR-3 field order."""
    print("Task ID: {}".format(task.get("id", "")))
    print("Title: {}".format(task.get("title", "")))
    print("Category: {}".format(task.get("category", "")))
    print("Due Date: {}".format(task.get("due_date", "")))
    status = "Completed" if task.get("completed") is True else "Pending"
    print("Status: {}".format(status))


def _handle_view():
    _success, message, tasks = task_manager.view_tasks()
    if not _success:
        _print_result(message)
        return
    if not tasks:
        print(_MSG_NO_TASKS)
        return
    for index, task in enumerate(tasks):
        if index:
            print()  # blank line between task blocks (PRD FR-3)
        _render_task(task)


def _handle_statistics():
    _success, message, stats = task_manager.get_statistics()
    if not _success:
        _print_result(message)
        return
    print("Total: {}".format(stats["total"]))
    print("Pending: {}".format(stats["pending"]))
    print("Completed: {}".format(stats["completed"]))
    print("Completion rate: {}%".format(stats["completion_rate"]))


# ---------------------------------------------------------------------------
# S-304: Complete Task + Delete Task flows (FR-4 / FR-5)
# ---------------------------------------------------------------------------

def _handle_complete():
    task_id = _prompt_task_id("complete")
    _success, message, _data = task_manager.complete_task(task_id)
    _print_result(message)


def _handle_delete():
    task_id = _prompt_task_id("delete")
    # Pre-check [USER-APPROVED]: existence check + detail display before the
    # confirmation prompt. task_manager.delete_task remains the second-layer
    # protection with its own not-found/corruption result tuples.
    task = task_manager.get_task(task_id)
    if task is None:
        print("Task not found.")
        return
    _render_task(task)
    confirm = input(_MSG_CONFIRM_DELETE).strip().lower()
    if confirm == "y":
        _success, message, _data = task_manager.delete_task(task_id)
        _print_result(message)
    else:
        print(_MSG_DELETE_CANCELLED)


# ---------------------------------------------------------------------------
# S-301: menu loop and dispatch (FR-7 interaction side)
# ---------------------------------------------------------------------------

_ACTIONS = {
    "1": _handle_add,
    "2": _handle_view,
    "3": _handle_complete,
    "4": _handle_delete,
    "5": _handle_statistics,
}


def run():
    """Menu loop: display menu, dispatch, return to menu until Exit (FR-7)."""
    while True:
        print(_MENU)
        choice = input("Select an option (1-6): ").strip()
        if choice == "6":
            return  # FR-8: clean exit; AD-4 guarantees nothing unsaved
        action = _ACTIONS.get(choice)
        if action is None:
            print(_MSG_INVALID_OPTION)
            continue
        action()
