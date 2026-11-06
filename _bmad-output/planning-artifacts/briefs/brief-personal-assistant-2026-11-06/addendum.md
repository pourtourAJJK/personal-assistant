# Addendum: QuickTask Product Brief

## Document Conflict Reconciliation

The original project documents contain a significant divergence between the product vision/rules and the functional requirements:

| Document | Described As | V1 Resolution |
|---|---|---|
| 01_产品愿景.md | React + Vite + Tailwind frontend, Django + DRF backend, RESTful API, local database | Web version deferred to future iteration |
| 02_规则文档.md | Same React + Django stack, front-back separation, RESTful API constraints | Technical constraints marked as "future iteration applicable" |
| 03_需求文档.md | Python 3 CLI program, JSON file storage, terminal menu interface | **This is the V1 scope** |

**Decision**: V1 is a Python 3 terminal program with JSON storage. The React + Django web architecture is a future iteration (V2.0). The codebase should be structured to facilitate this migration, but V1 has no web framework, no server, and no API.

## Target User Reconciliation

| Document | Target User |
|---|---|
| 01_产品愿景.md | 职场人士 (professionals managing multiple work tasks) |
| 03_需求文档.md | 在校大学生 (students and individuals managing study/work tasks) |

**Decision**: V1 targets professionals as the primary user, per the product vision. The tool is profession-agnostic in practice — anyone comfortable with the terminal can use it — but the vision and messaging are oriented toward professionals who need a unified task management entry point.

## Decisions Log

These decisions were made during the Product Brief conversation and recorded in `.memlog.md`:

1. **V1 scope**: Python 3 terminal program + JSON storage. React + Django is a future iteration.
2. **Target user**: Professionals (per product vision), not students (per requirements doc).
3. **Technical constraints**: V1 follows the requirements doc (Python 3 + JSON). Code structure should allow future migration to React + Django.
4. **Category management**: Free-text input in V1. No predefined categories or category CRUD. Deferred to V1.1.
5. **Search and filter**: Not in V1. Deferred to V1.1. V1 focuses on the core capture-track-complete loop.
6. **Task editing**: Not in V1. Users delete and re-create if they need to modify a task. Deferred to a future iteration.

## V1 Feature Boundary Summary

| Feature | In V1? | Deferred To |
|---|---|---|
| Add task | Yes | — |
| View tasks | Yes | — |
| Complete task (status change) | Yes | — |
| Delete task (with confirmation) | Yes | — |
| Task statistics | Yes | — |
| Task editing | No | Future iteration |
| Search (keyword) | No | V1.1 |
| Filter (by category/status) | No | V1.1 |
| Category management | No | V1.1 |
| Web UI (React) | No | V2.0 |
| Backend service (Django) | No | V2.0 |
| Cloud sync | No | Not planned |
| Multi-user | No | Not planned |
| AI features | No | V2.1 (exploratory) |

## Data Model (V1)

| Field | Type | Required | Description |
|---|---|---|---|
| id | String | Yes | Unique task identifier (e.g., TASK001) |
| title | String | Yes | Task name |
| category | String | Yes | Free-text category |
| due_date | String | Yes | Due date (YYYY-MM-DD format) |
| completed | Boolean | Yes | Completion status |
| created_at | String | Yes | Creation timestamp |

Storage path: `data/tasks.json`

## Project Structure (V1, per requirements doc)

```
personal-assistant/
├── README.md
├── src/
│   ├── main.py          # Entry point
│   ├── cli.py           # Terminal menu and user interaction
│   ├── task_manager.py  # Task CRUD and statistics logic
│   └── storage.py       # JSON file read/write
├── data/
│   └── tasks.json       # Local task data
└── docs/                # Original planning documents
```

The modular separation (storage / business logic / CLI) is deliberate: it enables a future migration to a layered web architecture (React frontend → Django API → database) without rewriting the core business logic.

## Original Documents Preserved

The three original planning documents (`01_产品愿景.md`, `02_规则文档.md`, `03_需求文档.md`) are preserved unchanged. This brief and its addendum supersede them only for V1 scope decisions. The original documents remain as historical context and will be referenced when planning future iterations.
