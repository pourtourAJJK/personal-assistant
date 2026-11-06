---
title: "Product Brief: QuickTask"
status: draft
created: 2026-11-06
updated: 2026-11-06
---

# Product Brief: QuickTask

## Executive Summary

QuickTask is a lightweight personal task management tool that helps professionals capture, organize, and track their daily work tasks through a simple terminal interface. It addresses a fundamental problem: work tasks scatter across chat logs, emails, sticky notes, and memory, making it hard to know what's pending, what's done, and what's falling through the cracks.

V1 is a Python 3 command-line program that stores tasks in a local JSON file. It focuses on a tight, reliable loop: add a task, see your tasks, mark them done, delete what's no longer relevant, and get a quick count of where things stand. No accounts, no cloud, no complexity — just a dependable tool that runs anywhere Python runs.

This is the foundation. The codebase is structured to migrate toward a React + Django web application in future iterations, but V1 deliberately keeps the surface area small to ensure the core task management loop is solid, reliable, and genuinely useful before expanding.

## The Problem

Professionals juggle multiple parallel work streams — daily tasks, project milestones, meeting follow-ups, and ad-hoc requests. These tasks arrive from different channels: a colleague's message, an email thread, a hallway conversation, a post-meeting action item. Without a unified capture point, tasks end up scattered.

The consequences are predictable:

- **Forgotten tasks**: Items buried in chat history or mentioned in passing get lost. No one reviews yesterday's Slack threads.
- **Unclear status**: Without a single view, it's hard to tell what's pending and what's done. Mental load increases as the task count grows.
- **No progress visibility**: When tasks live in different places, there's no way to see the overall picture — how many tasks, how many completed, how many still open.
- **Fragmented context**: A task noted in an email lacks a due date. A sticky note lacks a category. Without structure, retrieving and organizing tasks becomes its own overhead.

Existing solutions tend to be either too heavy (full project management suites with steep learning curves) or too loose (a text file, a notes app with no task semantics). QuickTask occupies this middle ground — it provides structure for organization without the overhead of a full suite.

## The Solution

A Python 3 terminal application that implements a clean task management loop:

1. **Add tasks** — capture title, category, and due date through a guided terminal prompt. The program validates input, generates a unique ID, and persists the task.
2. **View tasks** — see all tasks in a formatted list showing ID, title, category, due date, and status.
3. **Complete tasks** — mark a task as done by entering its ID. Status changes persist immediately.
4. **Delete tasks** — remove tasks that are no longer relevant, with a confirmation step to prevent accidental deletion.
5. **Task statistics** — get a quick summary: total count, pending count, completed count, and completion rate.

Data is stored in a local JSON file (`data/tasks.json`). The program loads tasks on startup and saves after every modification. No database server, no network dependency, no installation beyond Python 3.

The terminal interface is menu-driven: a numbered list of actions, a prompt for input, and clear feedback after each operation. It's designed for someone who lives in the terminal and wants task management without context-switching to a browser tab.

## What Makes This Different

QuickTask doesn't compete with Todoist, Asana, or Jira. It's not trying to be a platform. Its value proposition is specific:

- **Zero friction**: No sign-up, no login, no API keys, no cloud dependency. Clone the repo, run `python src/main.py`, start managing tasks.
- **Terminal-native**: For professionals who already work in the terminal, QuickTask fits into the existing workflow rather than demanding a context switch.
- **Local-first by design**: Data stays on the user's machine. No privacy concerns, no sync conflicts, no offline mode needed — it's always offline.
- **Honest about scope**: V1 does five things well rather than twenty things poorly. The boundary is explicit and intentional.

The "moat" is not technical. It's the discipline of keeping the tool simple and reliable while the codebase is structured for future growth. If QuickTask earns a place in someone's daily routine, that trust is the advantage.

## Who This Serves

**Primary user**: Professionals who manage multiple parallel work tasks and are comfortable with command-line tools. They work in terminal-heavy environments (development, ops, data work) and want a fast, no-nonsense way to capture and track tasks without leaving their workflow.

**Characteristics**:
- Has an estimated 10–50 active tasks at any given time across different work contexts.
- Currently relies on a mix of memory, sticky notes, chat messages, and mental tracking.
- Values speed and reliability over rich features.
- Wants a clear picture of what's pending and what's done without clicking through dashboards.

**Secondary user**: Anyone with terminal access who needs lightweight task tracking — students managing assignments, freelancers tracking client work, researchers organizing project tasks. The tool doesn't assume a specific profession; it assumes comfort with the terminal.

## Success Criteria

1. **Functional completeness**: A user can add, view, complete, delete, and get statistics on tasks — the full loop works without errors.
2. **Data reliability**: Tasks persist across program restarts. No data loss on normal operation. Corrupt JSON is detected and reported to the user, not silently overwritten.
3. **Input resilience**: Invalid input (empty titles, bad date formats, non-existent task IDs) produces clear error messages, never crashes the program.
4. **Usability feedback**: Every operation gives the user a clear success or failure message. The menu is self-explanatory. A new user can operate the tool without reading documentation.
5. **Architecture readiness**: Code is modular (storage logic, business logic, and CLI are distinct layers) so that migrating to a web architecture in a future iteration doesn't require a rewrite.
6. **Runnable delivery**: The program starts with a single `python src/main.py` command. README documents the real startup command. A screenshot demonstrates a working run.

## Scope

### V1 — In Scope

| Function | Description |
|---|---|
| Add task | Create a task with title, category (free text), and due date. Auto-generate ID and creation timestamp. |
| View tasks | Display all tasks in a formatted list with ID, title, category, due date, and status. |
| Complete task | Mark a task as completed by ID. |
| Delete task | Remove a task by ID, with confirmation prompt. |
| Task statistics | Show total, pending, completed counts and completion rate. |

**Technical constraints (V1)**:
- Language: Python 3
- Storage: Local JSON file (`data/tasks.json`)
- Interface: Terminal menu (CLI)
- No web framework, no database server, no API, no network dependency
- Code structure: modular separation (storage / business logic / CLI) to facilitate future migration

### V1 — Explicitly Out of Scope

| Item | Rationale |
|---|---|
| Task editing (modify title/category/due date) | To keep V1 scope tight; users can delete and re-create tasks if needed. Deferred to a future iteration. |
| Search and filter (by category, status, keyword) | V1 focuses on the core capture-track-complete loop. Deferred to V1.1. |
| Category management (predefined categories, category CRUD) | V1 uses free-text categories only. Deferred to V1.1. |
| Web UI (React + Vite + Tailwind) | Future iteration. V1 is terminal-only. |
| Backend service (Django + Django REST Framework, RESTful API) | Future iteration. V1 has no server component. |
| Multi-user support, team collaboration | Out of scope for the foreseeable future. |
| Cloud sync, online database | Out of scope. V1 is local-first. |
| Notifications (push, email, SMS) | Out of scope. |
| AI features (auto-generation, task decomposition) | Out of scope. |
| Third-party integrations (calendar sync, OAuth) | Out of scope. |

### Future Iterations (Roadmap Context)

- **V1.1**: Task editing, category management, search and filter
- **V1.2**: Due date reminders and notifications
- **V2.0**: Web UI (React + Django), migrate from JSON to database
- **V2.1**: Explore AI-assisted task planning

These are directional, not committed. Each will be evaluated against actual usage feedback before implementation.

## Vision

QuickTask starts as a terminal tool that does one thing well: keep your work tasks in one place. If it earns daily use, it grows with the user — first adding search and editing, then reminders, then a web interface for when the terminal isn't enough.

The long-term vision is a personal task management system that scales from the command line to the browser, from a single JSON file to a proper database, from manual entry to AI-assisted planning — without ever losing the simplicity and reliability that made it worth using in the first place.

The discipline that matters: every new feature has to earn its place. QuickTask's identity is "the tool that doesn't get in your way." If it stops being that, it stops being QuickTask.
