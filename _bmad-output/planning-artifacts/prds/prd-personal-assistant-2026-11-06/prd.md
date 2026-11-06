---
title: QuickTask
status: final
created: 2026-11-06
updated: 2026-11-06
---

# PRD: QuickTask

## 0. Document Purpose

This PRD defines the functional and quality requirements for QuickTask V1 — a Python 3 command-line personal task management tool. It is written for the developer implementing V1 and the course evaluator reviewing the deliverable. It builds on the Product Brief (`_bmad-output/planning-artifacts/briefs/brief-personal-assistant-2026-11-06/brief.md`) and the original planning documents (`01_产品愿景.md`, `02_规则文档.md`, `03_需求文档.md`), consolidating their decisions into a single requirements source. Technical implementation details live in `addendum.md`.

## 1. Vision

QuickTask is a terminal tool that helps professionals capture and track daily work tasks. Work tasks scatter across chat logs, emails, sticky notes, and memory — QuickTask provides a single entry point where tasks are recorded, viewed, completed, and tracked.

V1 is a Python 3 CLI program with JSON file storage. It deliberately keeps the feature set small: add a task, see your tasks, mark them done, delete what's no longer relevant, get a quick count. No accounts, no cloud, no web interface — it requires only a Python 3 installation.

The codebase separates data access logic, business logic, and CLI presentation to simplify a future migration to a React + Django web architecture. V1 itself has no web framework, no server, and no API.

## 2. Target User

### 2.1 Jobs To Be Done

- **Capture a task before I forget it.** I just got a new assignment and need to record it with a title, category, and due date in under 10 seconds.
- **See everything on my plate.** I want to open the tool and immediately see all my tasks with their status.
- **Mark something done.** I finished a task and want to update its status so my list reflects reality.
- **Clean up stale tasks.** A task is no longer relevant or was created by mistake — I want to remove it safely.
- **Know where I stand.** I want a quick count of total, pending, and completed tasks to gauge my progress.

### 2.2 Non-Users (v1)

- Users who need multi-device sync or cloud access.
- Users who require a graphical or web interface.
- Users who need team collaboration or task assignment.
- Users who need AI-assisted task planning or auto-decomposition.

### 2.3 Key User Journeys

**UJ-1. Wei captures a new work task between meetings.**
Wei, a project coordinator, receives a task via a quick hallway conversation between meetings. He opens the terminal, runs `python src/main.py`, selects "Add Task" from the menu, enters the title "Prepare Q4 report draft", category "Work", and due date "2026-11-15". The program validates the input, generates ID TASK001, confirms "Task created successfully", and returns to the main menu. He closes the terminal and heads to his next meeting.

**UJ-2. Wei checks his task list at the start of the day.**
Wei starts his morning by running the program and selecting "View Tasks". The program reads `data/tasks.json` and displays all tasks in a formatted list: ID, title, category, due date, and status. He sees 3 pending and 2 completed tasks. He now knows what to focus on today.

**UJ-3. Wei marks a task complete after finishing it.**
Wei finishes the Q4 report draft. He opens the program, selects "Complete Task", enters "TASK001". The program finds the task, sets `completed` to `true`, saves the JSON file, and confirms "Task TASK001 marked as complete!" The list now shows one fewer pending task.

**UJ-4. Wei removes a task created by mistake.**
Wei accidentally created a duplicate task. He selects "Delete Task", enters the task ID. The program displays the task details and asks "Are you sure? (y/n)". He confirms. The program removes the task, saves the file, and confirms "Task TASK003 deleted successfully!"

**UJ-5. Wei checks his progress at the end of the week.**
Wei selects "Task Statistics". The program reads all tasks and displays: total 10, pending 6, completed 4, completion rate 40%. He has a clear picture of his week's progress.

## 3. Glossary

- **Task** — A single unit of work tracked by the system. Has an ID, title, category, due date, completion status, and creation timestamp.
- **Task ID** — Unique string identifier for a task, formatted as `TASK` + zero-padded sequential number (e.g., TASK001, TASK002).
- **Category** — Free-text label the user assigns to group tasks (e.g., "Work", "Study", "Meeting"). No predefined category list in V1.
- **Due Date** — Date string in `YYYY-MM-DD` format indicating when the task should be completed. May be in the past (V1 does not flag overdue tasks or display them differently).
- **Completed** — Boolean field indicating task completion status. `false` = pending, `true` = done.
- **JSON Storage** — The local file `data/tasks.json` that persists all task data between program runs.
- **Main Menu** — The numbered terminal menu presented on program startup, listing all available actions.

## 4. Features

### 4.1 Task Creation

**Description:** The user can create a new task by entering a title, category, and due date through the terminal. The program validates all inputs, generates a unique Task ID and creation timestamp, and persists the task to JSON storage. Realizes UJ-1.

**Functional Requirements:**

#### FR-1: Add a task

The user can create a new task by providing a title, category, and due date through the terminal menu.

**Consequences (testable):**
- Selecting "Add Task" from the main menu prompts the user sequentially for title, category, and due date.
- Empty title input (after trimming whitespace) is rejected with message "Task title cannot be empty, please re-enter." and re-prompts.
- Empty category input is rejected with message "Task category cannot be empty, please re-enter." and re-prompts.
- Due date not matching `YYYY-MM-DD` format is rejected with message "Invalid date format, please use YYYY-MM-DD." and re-prompts.
- Invalid date values (e.g., 2026-13-45) are rejected with message "Invalid date value, please check the date." and re-prompts.
- On valid input, the system generates a unique Task ID in the format `TASK` + zero-padded 3-digit sequential number (TASK001, TASK002, ...).
- The system auto-generates `created_at` as the current date-time.
- The new task is appended to the existing task collection and saved to `data/tasks.json`.
- Success message displays: "Task created successfully! Task ID: {id}, Task title: {title}".
- After completion, the user returns to the main menu.

**Out of Scope:**
- Duplicate detection (same title + category + due date) — not validated in V1.
- Task editing after creation — deferred.

#### FR-2: Task ID generation

The system generates a unique, sequential Task ID for each new task.

**Consequences (testable):**
- IDs follow the format `TASK` + zero-padded 3-digit sequential number (TASK001, TASK002, ..., TASK999).
- The next ID is computed as the highest existing ID + 1.
- If no tasks exist, the first ID is TASK001.
- [ASSUMPTION] IDs are not reused after deletion — if TASK003 is deleted, the next new task is still TASK004, not TASK003.

### 4.2 Task Viewing

**Description:** The user can view all stored tasks in a formatted list. The program reads from JSON storage and displays each task's ID, title, category, due date, and status. Realizes UJ-2.

**Functional Requirements:**

#### FR-3: View all tasks

The user can view all tasks stored in the system.

**Consequences (testable):**
- Selecting "View Tasks" from the main menu reads `data/tasks.json` and displays all tasks.
- Each task is displayed with: Task ID, title, category, due date, and status ("Pending" or "Completed").
- Tasks are displayed one per block, with each field on a separate line (ID, title, category, due date, status), separated by a blank line between tasks.
- If no tasks exist, the system displays "No tasks recorded yet."
- If the JSON file does not exist or is empty, the system displays "No tasks recorded yet." without crashing.
- If the JSON file is corrupt, the system displays "Data file is corrupted, unable to read tasks. Please check data/tasks.json." and does not overwrite the file.
- After displaying, the user returns to the main menu.

**Out of Scope:**
- Sorting (by date, by status, etc.) — not in V1.
- Pagination — all tasks shown at once.

### 4.3 Task Completion

**Description:** The user can mark a task as completed by entering its Task ID. The program finds the task, updates its `completed` field, and persists the change. Realizes UJ-3.

**Functional Requirements:**

#### FR-4: Mark a task as completed

The user can change a task's status from pending to completed by providing its Task ID.

**Consequences (testable):**
- Selecting "Complete Task" from the main menu prompts the user for a Task ID.
- If the Task ID exists, the system sets `completed` to `true`, saves to `data/tasks.json`, and displays "Task {id} marked as complete!"
- If the Task ID does not exist, the system displays "Task not found, please check the Task ID."
- If the task is already completed, the system displays "Task {id} is already completed."
- After the operation, the user returns to the main menu.

**Out of Scope:**
- Reverting a completed task back to pending — not in V1. [ASSUMPTION] This is acceptable; users can delete and re-create if needed.

### 4.4 Task Deletion

**Description:** The user can delete a task by entering its Task ID. The program displays the task details and asks for confirmation before removing it. Realizes UJ-4.

**Functional Requirements:**

#### FR-5: Delete a task

The user can delete a task by providing its Task ID, with a confirmation step.

**Consequences (testable):**
- Selecting "Delete Task" from the main menu prompts the user for a Task ID.
- If the Task ID exists, the system displays the task details (ID, title, category, due date, status) and prompts "Are you sure you want to delete this task? (y/n)".
- On "y" confirmation, the system removes the task from the collection, saves to `data/tasks.json`, and displays "Task {id} deleted successfully!"
- On "n" or any other input, the system displays "Delete operation cancelled." and does not modify any data.
- If the Task ID does not exist, the system displays "Task not found."
- Deleting a task does not affect any other task in the collection.
- After the operation, the user returns to the main menu.

### 4.5 Task Statistics

**Description:** The user can view a summary of task counts: total, pending, completed, and completion rate. The program reads all tasks and computes the statistics. Realizes UJ-5.

**Functional Requirements:**

#### FR-6: View task statistics

The user can view a summary of task counts and completion rate.

**Consequences (testable):**
- Selecting "Task Statistics" from the main menu reads `data/tasks.json` and computes statistics.
- The system displays: total task count, pending count (`completed == false`), completed count (`completed == true`), and completion rate (completed / total, as a percentage).
- If no tasks exist, the system displays total: 0, pending: 0, completed: 0, completion rate: 0% — no division-by-zero error.
- Statistics are computed from actual stored data, not cached or approximate values.
- After displaying, the user returns to the main menu.

### 4.6 Program Entry and Exit

**Description:** The program starts with a main menu and allows the user to exit cleanly.

**Functional Requirements:**

#### FR-7: Start and display main menu

The program starts with a single command and presents a numbered main menu.

**Consequences (testable):**
- Running `python src/main.py` starts the program.
- On startup, the program loads existing tasks from `data/tasks.json`.
- If `data/tasks.json` does not exist, the program creates the `data/` directory and initializes an empty task list — no crash.
- The main menu displays numbered options: 1. Add Task, 2. View Tasks, 3. Complete Task, 4. Delete Task, 5. Task Statistics, 6. Exit.
- The program loops back to the main menu after each operation until the user selects Exit.

#### FR-8: Exit the program

The user can exit the program cleanly.

**Consequences (testable):**
- Selecting "Exit" from the main menu terminates the program.
- No data is lost on exit (all modifications are saved immediately when they occur).

## 5. Non-Goals (Explicit)

- **Task editing** — V1 does not support modifying a task's title, category, or due date after creation. Users delete and re-create if needed. *(Original vision/rules docs listed editing as V1 P0; scope reduced during Product Brief — see Brief addendum.)*
- **Search and filter** — V1 does not support searching by keyword or filtering by category/status. All tasks are shown in the view list. *(Original vision/rules docs listed this as V1 P0; scope reduced during Product Brief.)*
- **Category management** — V1 does not provide predefined categories or category CRUD. Categories are free-text.
- **Web UI** — No graphical or web interface in V1. Terminal only.
- **Backend service** — No Django, no REST API, no server component in V1.
- **Multi-user** — No user accounts, no authentication, no collaboration.
- **Cloud sync** — Data is local only. No sync, no online database.
- **Notifications** — No push, email, or SMS reminders.
- **AI features** — No auto-generation, task decomposition, or smart planning.
- **Third-party integrations** — No calendar sync, no OAuth, no external API calls.

## 6. V1 Scope

### 6.1 In Scope

- Task creation with title, category, due date; auto-generated ID and timestamp (FR-1, FR-2)
- Task viewing: formatted list of all tasks (FR-3)
- Task completion: mark done by ID (FR-4)
- Task deletion: remove by ID with confirmation (FR-5)
- Task statistics: total, pending, completed, completion rate (FR-6)
- Program entry, menu, and exit (FR-7, FR-8)
- JSON file persistence (`data/tasks.json`)
- Terminal menu interface
- Input validation and error handling for all operations
- Corrupt JSON file protection (detect and report, never silently overwrite)

### 6.2 Out of Scope for V1

- Task editing — deferred to a future iteration
- Search and filter — deferred to V1.1
- Category management — deferred to V1.1
- Web UI (React + Django) — deferred to V2.0
- Reminders and notifications — deferred to V1.2
- AI features — deferred to V2.1 (exploratory)

## 7. Cross-Cutting NFRs

### 7.1 Reliability
- Data modifications (add, complete, delete) are saved to `data/tasks.json` immediately — no buffered writes that could lose data on crash.
- Corrupt JSON is detected and reported; the original file is never silently overwritten.
- Invalid input never crashes the program; all user input is validated before processing.

### 7.2 Maintainability
- Code is organized into modules with clear separation: `storage.py` (JSON read/write), `task_manager.py` (business logic), `cli.py` (terminal interaction), `main.py` (entry point).
- Data access logic is separated from business logic to facilitate future migration to a web architecture.
- Code includes necessary comments for non-obvious logic.

### 7.3 Security
- No real identity information collected.
- No account passwords stored.
- No third-party API keys or credentials used.
- No local task data uploaded to any external service.
- All data remains on the user's local machine.

### 7.4 Usability
- Terminal menu is clear and self-explanatory; a new user can operate the tool without reading documentation.
- Every operation provides clear success or failure feedback.
- Error messages guide the user toward correction, not just state what went wrong.

## 8. Success Metrics

**Primary**
- **SM-1**: Functional completeness — all 6 core functional acceptance criteria pass: task can be added and saved, tasks can be viewed correctly, task status can be changed, task can be deleted and saved, statistics compute correctly. Validates FR-1 through FR-6. (Corresponds to items 2–6 in 03_需求文档.md §七 整体验收标准.)

**Secondary**
- **SM-2**: Data persistence — program starts via `python` command, tasks survive program restart, no data lost on exit. Validates FR-7, FR-8. (Corresponds to items 1, 7 in 03_需求文档.md §七.)
- **SM-3**: Error resilience — invalid input (empty title, bad date, non-existent ID) produces clear error messages without crashing. Validates FR-1, FR-3, FR-4, FR-5, FR-6.
- **SM-4**: Delivery completeness — README documents the real startup command; at least one screenshot demonstrates a working run. (Corresponds to item 9 in 03_需求文档.md §七.)

**Counter-metrics (do not optimize)**
- **SM-C1**: Feature count — do not add features beyond V1 scope to inflate the count. Scope discipline is more valuable than feature breadth for this iteration.

## 9. Open Questions

1. **ID reuse after deletion** — [ASSUMPTION] IDs are not reused. If TASK003 is deleted, the next task is TASK004. Confirm this is acceptable, or should IDs be reused?
2. **Complete-to-pending revert** — [ASSUMPTION] V1 does not support reverting a completed task back to pending. Is this acceptable?
3. **Date validation strictness** — [ASSUMPTION] Past due dates are allowed (for recording retroactive tasks). Should past dates be rejected instead?
4. **`updated_at` field** — [ASSUMPTION] Not implemented in V1 because task editing (which would update this field) is out of scope. Confirm this is acceptable.
5. **`due_date` required vs optional** — [ASSUMPTION] `due_date` is required (per 03_需求文档.md). The rules doc (02_规则文档.md) allows it to be optional. PRD follows the requirements doc. Confirm.

## 10. Assumptions Index

- `[ASSUMPTION]` §4.1 FR-2 — Task IDs are not reused after deletion; next ID is always max existing + 1.
- `[ASSUMPTION]` §4.3 FR-4 — Reverting a completed task to pending is not supported in V1.
- `[ASSUMPTION]` §9 Q3 — Due dates in the past are allowed; the system does not reject past dates.
- `[ASSUMPTION]` §9 Q4 — `updated_at` field not implemented (consequence of excluding task editing).
- `[ASSUMPTION]` §9 Q5 — `due_date` is required, following 03_需求文档.md over 02_规则文档.md.
