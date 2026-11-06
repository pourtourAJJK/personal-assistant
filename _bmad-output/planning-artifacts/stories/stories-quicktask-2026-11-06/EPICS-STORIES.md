---
name: QuickTask V1 Epics & Stories
type: epic-story-breakdown
purpose: build-guidance
altitude: story
sources: [prd-personal-assistant-2026-11-06, architecture-personal-assistant-2026-11-06 (Rev-2 spine), brief-personal-assistant-2026-11-06 + addendum]
status: draft
created: 2026-11-06
updated: 2026-11-06
baseline: ARCHITECTURE-SPINE.md Rev-2（唯一技术基线，接口签名与数据结构不得偏离）
---

# QuickTask V1 — Epic / Story 拆分

## 拆分原则

1. **以 Rev-2 脊柱为唯一基线**：每个 Story 的「对应接口」直接引用脊柱 Interface Contracts 章节，签名一字不改。
2. **依赖方向即开发方向**：Story 依赖关系严格遵循 AD-1 分层（storage → task_manager → cli → main），下层 Story 先完成并独立验收后，上层才开工。
3. **每个 Story 独立可验收**：验收标准全部来自 PRD 的可测试后果（testable consequences）+ 脊柱 AD 规则，可用 `python -m unittest` 或手工终端操作验证。
4. **不加不减**：不引入 React / Django / 数据库 / AI API；不删减 PRD 已确定的 8 项 FR；V1 Non-Goals（编辑、搜索、分类管理等）不出现任何 Story。

## Epic 总览

| Epic | 名称 | 覆盖 | Stories |
| --- | --- | --- | --- |
| E1 | 数据持久化基座 | AD-3, AD-7, FR-3/FR-7 的存储语义 | S-101, S-102 |
| E2 | 业务逻辑核心 | AD-2, AD-4, AD-5, AD-6, AD-7, FR-1~FR-6 | S-201 ~ S-206 |
| E3 | 终端交互层 | AD-2 校验分工, AD-6 消息归属, FR-1/3/4/5/6 交互 | S-301 ~ S-304 |
| E4 | 程序组装与交付 | AD-1, FR-7, FR-8, SM-1~SM-4 | S-401 ~ S-403 |

---

## Epic E1 — 数据持久化基座（storage.py）

### S-101 · 存储·读取路径 load_tasks()

- **Story ID:** S-101
- **功能名称:** JSON 数据读取（缺失 / 空 / 正常 / 损坏四态语义）
- **用户故事:** 作为开发者，我需要一个语义完全确定的读取函数，使所有上层模块在文件缺失、为空、损坏时行为一致且可预测。
- **涉及模块:** `src/storage.py`
- **输入与输出:**
  - 输入：`data/tasks.json` 的文件系统状态（不存在 / 0 字节 / 合法 JSON 数组 / 损坏内容 / 根节点非数组）
  - 输出：`list[dict]`；损坏时抛 `json.JSONDecodeError`，根节点非数组时抛 `ValueError`
- **具体实现要求:**
  1. 文件路径为 `storage.py` 内部常量（AD-3），模块内仅此一处引用路径。
  2. `data/` 目录或 `tasks.json` 不存在 → 返回 `[]`，不抛异常、不创建任何文件/目录（懒初始化留给 save）。
  3. 文件存在但 0 字节 → 返回 `[]`（视为空，非损坏）。
  4. 读文件强制 `open(..., encoding="utf-8")`（AD-3），禁止平台默认编码。
  5. 非空文件 `json.loads` 失败 → 抛 `json.JSONDecodeError`（不捕获、不修复、不重写文件）；解析成功但根节点不是数组 → 抛 `ValueError`（AD-7 损坏定义）。
  6. 公开函数仅有 `load_tasks() -> list`，不得额外导出任何函数（AD-3）。
- **验收标准:**
  - [ ] 四态单测通过（unittest，stdlib）：缺失→`[]`；0 字节→`[]`；合法内容→按序返回等长任务列表；损坏 JSON→抛 `JSONDecodeError` 且**文件字节不变**；根为对象 → 抛 `ValueError`。
  - [ ] 含中文任务内容的文件正确读出（UTF-8 断言）。
  - [ ] `storage.py` 中路径字符串只出现一次（代码检查）。
- **依赖关系:** 无（首个 Story）。
- **对应接口:** `storage.load_tasks() -> list`（脊柱 Interface Contracts）

### S-102 · 存储·写入路径 save_tasks()（原子写）

- **Story ID:** S-102
- **功能名称:** JSON 原子写入 + 目录懒创建
- **用户故事:** 作为用户，我希望任何一次保存要么完整成功、要么完全不发生，程序崩溃也不能留下半个文件或丢掉已有数据。
- **涉及模块:** `src/storage.py`
- **输入与输出:**
  - 输入：`tasks: list[dict]`（完整的任务数组，来自 task_manager 现读现改的结果）
  - 输出：`None`；副作用为 `data/tasks.json` 被整体原子替换；`data/` 目录缺失时自动创建
- **具体实现要求:**
  1. `os.makedirs("data", exist_ok=True)`（FR-7 首次初始化的真实落点；PRD 的「启动创建目录」语义由首次保存实现——见《开发规划》§4 待确认项 1）。
  2. 原子写三步（AD-3）：`json.dump` 写入**同目录临时文件** → `os.replace(temp, tasks.json)` → 无直接对目标路径的 `json.dump`。临时文件用 `tempfile.NamedTemporaryFile(dir="data", delete=False)` 或等效方式，替换后确保无残留。
  3. `encoding="utf-8"` + `ensure_ascii=False` + `indent=2`（AD-3；indent 使评估者可直接阅读文件，不违反任何 AD）。
  4. 公开函数仅有 `save_tasks(tasks: list) -> None`。
- **验收标准:**
  - [ ] 保存→读取 round-trip 一致（含中文字段，文件内容人类可读）。
  - [ ] 删除 `data/` 目录后调用 `save_tasks` 不报错且目录被创建。
  - [ ] 代码检查确认：目标文件只通过 `os.replace` 被触碰；写失败场景下原文件保持旧内容。
  - [ ] 临时文件在成功路径上不残留。
- **依赖关系:** 无（与 S-101 并行可做，但同文件建议串行）。
- **对应接口:** `storage.save_tasks(tasks: list) -> None`（脊柱 Interface Contracts）

---

## Epic E2 — 业务逻辑核心（task_manager.py）

> E2 全部 Story 共同遵守：**无模块级任务缓存**（AD-4）——每个操作函数内部先 `load_tasks()` 现读，变更后立即 `save_tasks()`；只捕获 storage 异常（AD-6），除脊柱列出的公开函数外不得新增公开接口（私有辅助函数如 `_build_task` 允许）。

### S-201 · ID 生成与 Task 实体构造

- **Story ID:** S-201
- **功能名称:** `generate_task_id()` + Task dict 构造（AD-2 / AD-5）
- **用户故事:** 作为系统，我需要一个无歧义的 ID 生成契约和唯一实体形状，使任何后续功能都不会产生 ID 冲突或字段漂移。
- **涉及模块:** `src/task_manager.py`
- **输入与输出:**
  - 输入：`generate_task_id(tasks: list)`——现读出的任务列表；实体构造输入为已通过 cli 校验的 `title/category/due_date` 三个 str
  - 输出：ID 字符串（`TASK` + 至少 3 位零填充）；Task dict（`id, title, category, due_date, completed=False, created_at`）
- **具体实现要求:**
  1. ID = `max(现存数字后缀) + 1`，零填充至少 3 位；无任务 → `TASK001`；超 999 自然进位 `TASK1000`；删除不复用；解析 max 时跳过 `id` 缺失或格式畸形的记录（AD-5 全部四点）。
  2. `created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")`——禁止 `isoformat()`（含微秒，AD-2）。
  3. `due_date` 允许过去日期（PRD §9 Q3），构造层不做日期范围判断。
  4. 实体构造为**私有**辅助（如 `_build_task`），公开契约只有 `generate_task_id`。
- **验收标准:**
  - [ ] 空列表 → `TASK001`；`[TASK001, TASK002]` → `TASK003`；删掉 TASK003 后 → 仍 `TASK004`；含 `TASK999` → `TASK1000`。
  - [ ] 列表中混入 `id` 畸形记录（如 `"abc"`、缺 `id`）不崩溃且不参与 max。
  - [ ] 构造的 dict 恰好 6 个键、类型正确、`created_at` 长度为 19 且无微秒。
- **依赖关系:** S-101（需要真实数据结构做集成验证；纯逻辑可先行，验收需 S-101）。
- **对应接口:** `generate_task_id(tasks: list) -> str`（脊柱 Interface Contracts）

### S-202 · add_task()

- **Story ID:** S-202
- **功能名称:** 添加任务（FR-1 + FR-2 业务侧）
- **用户故事:** 作为职场人士，我录入标题、分类、截止日期后，系统生成唯一 ID 并立即持久化，我立刻得到含 ID 的成功确认。
- **涉及模块:** `src/task_manager.py`
- **输入与输出:**
  - 输入：`title: str, category: str, due_date: str`（已由 cli 完成原始输入校验）
  - 输出：`(True, "Task created successfully! Task ID: {id}, Task title: {title}", new_id)` 或失败元组
- **具体实现要求:**
  1. 流程（AD-4）：`load_tasks()` 现读 → `generate_task_id` → `_build_task` 构造实体 → append → 立即 `save_tasks()`。
  2. 失败路径（AD-7）：`load_tasks()` 抛 `JSONDecodeError`/`ValueError` → 返回 `(False, <损坏文案>, None)`，**绝不调用 save_tasks**。
  3. 构造后防御性校验失败（AD-2 第二阶段）→ `(False, <失败文案>, None)`，不落盘。
  4. 成功文案为 PRD 固定格式，属 task_manager 消息集（AD-6）。
- **验收标准:**
  - [ ] 正常添加 → 返回 `(True, ..., "TASK00x")`，文件中出现恰好一条新记录、字段完整。
  - [ ] 连续添加 3 条，ID 严格递增不重复。
  - [ ] 预置损坏文件后调用 → 返回 `(False, ...)`，文件字节不变（AD-7 关键断言）。
- **依赖关系:** S-101, S-102, S-201。
- **对应接口:** `add_task(title: str, category: str, due_date: str) -> tuple`

### S-203 · view_tasks() + get_task()

- **Story ID:** S-203
- **功能名称:** 全量读取 + 按 ID 精确查找（FR-3 业务侧，FR-5 确认展示的数据源）
- **用户故事:** 作为职场人士，我打开程序就能基于磁盘上的真实数据看到全部任务；删除前系统也能按 ID 取到单条详情。
- **涉及模块:** `src/task_manager.py`
- **输入与输出:**
  - 输入：无参数 / `task_id: str`
  - 输出：`view_tasks() -> (True, "", tasks_list)`（空列表同样 `(True, "", [])`，由 cli 显示 "No tasks recorded yet."）；损坏 → `(False, <损坏文案>, None)`；`get_task(task_id) -> dict | None`
- **具体实现要求:**
  1. 现读磁盘，不缓存（AD-4；满足 PRD FR-6 "not cached" 对所有读路径的延伸）。
  2. `get_task` 按 `id` 精确匹配第一个命中的任务；不命中返回 `None`（不是异常）。
  3. 成功时 `message` 为空串——列表渲染是 cli 的展示职责（AD-6 消息二分）。
- **验收标准:**
  - [ ] 文件含 N 条记录 → 返回等长列表且顺序与文件一致。
  - [ ] 文件为空/缺失 → `(True, "", [])`，不抛异常。
  - [ ] 损坏文件 → `(False, ...)` 且文件不被改动。
  - [ ] `get_task("TASK002")` 返回正确 dict；`get_task("TASKXXX")` 返回 `None`。
- **依赖关系:** S-101。
- **对应接口:** `view_tasks() -> tuple`；`get_task(task_id: str) -> dict | None`

### S-204 · get_statistics()

- **Story ID:** S-204
- **功能名称:** 任务统计（FR-6 业务侧）
- **用户故事:** 作为职场人士，周末我想一眼看到总量、待办、完成数和完成率，数据必须来自真实存储而非缓存。
- **涉及模块:** `src/task_manager.py`
- **输入与输出:**
  - 输入：无参数
  - 输出：`(True, "", {"total": int, "pending": int, "completed": int, "completion_rate": int})`；损坏 → `(False, <损坏文案>, None)`
- **具体实现要求:**
  1. 现读现算（AD-4）；`pending = completed == False` 计数，`completed = completed == True` 计数。
  2. `completion_rate = round(completed / total * 100)`（0–100 整数）；**空列表时全 0，不触发除零**（PRD FR-6）。
  3. 百分比格式化（"40%"）是 cli 展示职责，task_manager 只给整数。
- **验收标准:**
  - [ ] 10 条（4 完成）→ `{"total": 10, "pending": 6, "completed": 4, "completion_rate": 40}`（对应 PRD UJ-5）。
  - [ ] 空文件 → 全 0，无异常。
  - [ ] 损坏文件 → `(False, ...)` 且文件不变。
- **依赖关系:** S-101。
- **对应接口:** `get_statistics() -> tuple`

### S-205 · complete_task()

- **Story ID:** S-205
- **功能名称:** 标记完成（FR-4 业务侧）
- **用户故事:** 作为职场人士，我输入任务 ID 把它标记为完成，状态立即持久化；重复标记得到友好提示而不是错误。
- **涉及模块:** `src/task_manager.py`
- **输入与输出:**
  - 输入：`task_id: str`
  - 输出：成功 `(True, "Task {id} marked as complete!", None)`；已completed → `(True, "Task {id} is already completed.", None)`；不存在 → `(False, "Task not found, please check the Task ID.", None)`；损坏 → `(False, <损坏文案>, None)`
- **具体实现要求:**
  1. 现读 → 查找 → 幂等分支（已 completed 返回成功+信息文案，脊柱 Interface Contracts 已钉死）→ 置 `completed = True` → 立即 `save_tasks()`。
  2. 不支持回退 completed→pending（PRD FR-4 Out of Scope），不实现该分支。
- **验收标准:**
  - [ ] 完成 TASK001 → 文件中该记录 `completed == True`（bool 而非字符串），其余记录不变。
  - [ ] 再次完成同一 ID → `(True, "already completed", None)`，文件不变。
  - [ ] 不存在 ID → `(False, ...)`，文件不变；损坏文件 → `(False, ...)` 且**绝不写盘**（AD-7）。
- **依赖关系:** S-101, S-102。
- **对应接口:** `complete_task(task_id: str) -> tuple`

### S-206 · delete_task()

- **Story ID:** S-206
- **功能名称:** 删除任务（FR-5 业务侧）
- **用户故事:** 作为职场人士，确认删除后任务被安全移除并立即持久化，其他任务不受任何影响。
- **涉及模块:** `src/task_manager.py`
- **输入与输出:**
  - 输入：`task_id: str`
  - 输出：成功 `(True, "Task {id} deleted successfully!", None)`；不存在 → `(False, "Task not found.", None)`；损坏 → `(False, <损坏文案>, None)`
- **具体实现要求:**
  1. 现读 → 按 ID 移除（仅移除一个命中项）→ 立即 `save_tasks()`。
  2. ID 不复用逻辑无需此处处理（AD-5 在生成侧保证）。
  3. 注意文案差异：删除路径的 not found 文案是 "Task not found."（PRD FR-5），与 FR-4 的长文案不同——两套固定文案都归 task_manager 消息集。
- **验收标准:**
  - [ ] 删除 TASK002 → 文件少恰好一条，其余记录字节级不变（仅少一条）。
  - [ ] 删除后新建任务 ID 不复用被删号（与 S-201 联测）。
  - [ ] 不存在 ID / 损坏文件 → 失败元组，文件不变。
- **依赖关系:** S-101, S-102。
- **对应接口:** `delete_task(task_id: str) -> tuple`

---

## Epic E3 — 终端交互层（cli.py）

> E3 全部 Story 共同遵守 AD-6 消息二分：cli 只输出 menu/prompt/重试提示 + **原样透传** task_manager 返回的 message；cli 中禁止 try/except 捕获 storage 异常、禁止裸 `except:`（KeyboardInterrupt 自然传播）。

### S-301 · 菜单循环与输入校验框架

- **Story ID:** S-301
- **功能名称:** 主菜单循环、选项分发、原始输入校验（FR-1 校验规则 + FR-7 菜单）
- **用户故事:** 作为新用户，不读文档也能看懂菜单并按提示操作；输错内容时被温和地重新提示而不是崩溃。
- **涉及模块:** `src/cli.py`
- **输入与输出:**
  - 输入：stdin（菜单选项 1–6；标题/分类/日期文本；y/n 确认）
  - 输出：stdout（菜单、"请输入…" 提示、重试提示）；内部产出经校验的 `(title, category, due_date)` 传给 task_manager
- **具体实现要求:**
  1. 菜单文案为 PRD 固定六项：`1. Add Task / 2. View Tasks / 3. Complete Task / 4. Delete Task / 5. Task Statistics / 6. Exit`；每步操作后回到菜单，仅 6 退出（FR-7）。
  2. 校验辅助（私有函数）：`_prompt_title`（strip 后非空，否则 "Task title cannot be empty, please re-enter." 重试）、`_prompt_category`（同规则）、`_prompt_due_date`（先 `strptime("%Y-%m-%d")` 格式校验，格式错 → "Invalid date format, please use YYYY-MM-DD."；数值非法如 13 月 → "Invalid date value, please check the date."；**过去日期不拒绝**）。
  3. 校验通过后才调用 task_manager——原始输入校验归 cli、实体校验归 task_manager（AD-2 校验二分，各一遍，不重复）。
  4. 结果元组展示辅助：统一打印 `message`；`view_tasks`/`get_statistics` 的空 message 情形由各流程 Story 处理。
- **验收标准:**
  - [ ] 空标题 / 空分类输入 → 精确复现 PRD 重试文案并重新提示，直至合法。
  - [ ] "2026-13-45" → "Invalid date value…"；"2026/11/15" → "Invalid date format…"；"2025-01-01"（过去）→ 通过。
  - [ ] 菜单循环：非法选项（0、9、"abc"）→ 重新显示菜单，不崩溃；选 6 干净退出。
  - [ ] 代码检查：`cli.py` 无 `import json`、无 storage import、无裸 except（AD-1 / AD-6）。
- **依赖关系:** 无硬依赖（校验辅助为纯函数可先测）；菜单分发接线在 S-302~304 完成。
- **对应接口:** 消费 `add_task / view_tasks / complete_task / delete_task / get_statistics / get_task`（签名见脊柱契约，本 Story 仅搭框架）

### S-302 · 添加任务交互流

- **Story ID:** S-302
- **功能名称:** Add Task 全流程（FR-1 交互侧）
- **用户故事:** 作为职场人士，我选 1 后被依次引导输入三项内容，成功后看到含 ID 的确认并回到菜单。
- **涉及模块:** `src/cli.py`（调用 `task_manager.add_task`）
- **输入与输出:**
  - 输入：依次提示的 title / category / due_date
  - 输出：task_manager 的成功/失败 message 原样显示 → 回到主菜单
- **具体实现要求:**
  1. 串联 S-301 的三个 `_prompt_*` → 调 `add_task` → 打印返回 message（不加工、不新增文案）。
  2. 失败元组（如损坏）同样显示后回菜单——错误后不退出程序（PRD 各 FR 均要求 "returns to the main menu"）。
- **验收标准:**
  - [ ] 合法输入 → 显示 "Task created successfully! Task ID: TASK00x, Task title: …" 后回菜单。
  - [ ] 损坏文件场景 → 显示损坏文案后回菜单，文件不被写。
- **依赖关系:** S-301, S-202。
- **对应接口:** `add_task(title, category, due_date) -> tuple`

### S-303 · 查看与统计交互流

- **Story ID:** S-303
- **功能名称:** View Tasks + Task Statistics 展示（FR-3 / FR-6 交互侧）
- **用户故事:** 作为职场人士，我选 2 看到逐字段分块的任务列表，选 5 看到统计摘要，空数据时得到友好空态提示。
- **涉及模块:** `src/cli.py`（调用 `view_tasks` / `get_statistics`）
- **输入与输出:**
  - 输入：菜单选项 2 / 5
  - 输出：任务列表（每条 ID、标题、分类、日期、状态各一行，任务间空行分隔，状态显示 "Pending"/"Completed"）；统计四项；空态 "No tasks recorded yet."
- **具体实现要求:**
  1. 列表渲染字段顺序硬编码为 ID → title → category → due_date → status（PRD FR-3 展示顺序，不依赖 dict 键序）。
  2. 空列表（`data == []`）→ "No tasks recorded yet."（该文案是 cli 展示职责，AD-6）。
  3. 统计渲染：`Total: {t} / Pending: {p} / Completed: {c} / Completion rate: {rate}%`；`rate` 直接用返回整数。
  4. 失败元组（损坏）→ 原样显示 message（此时即 PRD 的 "Data file is corrupted…" 文案，来自 task_manager）。
- **验收标准:**
  - [ ] 预置 3 条任务（2 pending 1 completed）→ 展示顺序、字段、状态词精确匹配 PRD FR-3。
  - [ ] 空文件 → "No tasks recorded yet."，不崩溃。
  - [ ] 统计显示与预置数据吻合（如 UJ-5 的 10/6/4/40%）；空文件显示全 0。
- **依赖关系:** S-301, S-203, S-204。
- **对应接口:** `view_tasks() -> tuple`；`get_statistics() -> tuple`

### S-304 · 完成与删除交互流

- **Story ID:** S-304
- **功能名称:** Complete Task + Delete Task（含删除确认）（FR-4 / FR-5 交互侧）
- **用户故事:** 作为职场人士，我按 ID 完成或删除任务；删除前系统先展示详情并要我确认，取消则什么也不发生。
- **涉及模块:** `src/cli.py`（调用 `get_task` / `complete_task` / `delete_task`）
- **输入与输出:**
  - 输入：任务 ID；删除确认 y/n
  - 输出：完成/删除的 message；确认前展示任务详情（ID、标题、分类、日期、状态）；取消时 "Delete operation cancelled."
- **具体实现要求:**
  1. Complete 流程：提示输入 ID → `complete_task` → 显示 message（含 not-found / already-completed 两分支）。
  2. Delete 流程（PRD FR-5 顺序）：提示输入 ID → `get_task(id)`：`None` → 显示 "Task not found."（此分支 cli 直接判定，不走 delete_task）；有详情 → 展示 → 提示 "Are you sure you want to delete this task? (y/n)" → `y` 调 `delete_task` 并显示其 message；`n` 或其他任意输入 → "Delete operation cancelled." 且**不触碰数据**。
  3. "Delete operation cancelled." 属 cli 交互消息集（AD-6 二分）。
- **验收标准:**
  - [ ] 完成流程三分支（成功 / 已完成 / 不存在）文案与 PRD FR-4 逐字一致。
  - [ ] 删除确认展示四字段详情；y → 删除成功文案；n / 回车 / 乱输入 → cancelled 且文件字节不变。
  - [ ] 删除不存在的 ID → "Task not found."，且**不进入确认环节**。
- **依赖关系:** S-301, S-203（get_task）, S-205, S-206。
- **对应接口:** `get_task(task_id) -> dict | None`；`complete_task(task_id) -> tuple`；`delete_task(task_id) -> tuple`

---

## Epic E4 — 程序组装与交付

### S-401 · 程序入口 main.py

- **Story ID:** S-401
- **功能名称:** 入口接线（FR-7 / FR-8）
- **用户故事:** 作为用户，我在项目根目录运行 `python src/main.py` 即进入菜单，首次运行无需任何准备步骤，退出时数据已安全。
- **涉及模块:** `src/main.py`
- **输入与输出:**
  - 输入：命令行启动
  - 输出：进入 cli 菜单循环；退出码 0
- **具体实现要求:**
  1. `main()` 唯一职责：调用 `cli.run()`（脊柱契约）；`if __name__ == "__main__": main()`。
  2. 首次启动路径：`data/` 缺失时菜单照常显示、查看显示空态、首次保存时自动建目录（S-102 懒初始化）——**不在 main 中做任何初始化调用**（AD-1：main 只 import cli）。
  3. 退出即菜单选 6，无额外清理逻辑（AD-4 保证无未落盘数据）。
- **验收标准:**
  - [ ] 全新环境（无 `data/`）运行 → 菜单正常显示，Add 一条后 `data/tasks.json` 出现且内容正确。
  - [ ] 重启程序 → 数据仍在（SM-2）。
  - [ ] `main.py` 中 import 仅有 `cli`（AD-1 代码检查）。
- **依赖关系:** S-301（run 入口存在）。
- **对应接口:** `main.main() -> None`

### S-402 · 集成测试与异常处理验证

- **Story ID:** S-402
- **功能名称:** 端到端验收 + 错误韧性专项（SM-1 / SM-2 / SM-3；AD-6 / AD-7 全链路）
- **用户故事:** 作为课程评估者，我按 PRD 验收标准逐条操作，全部通过且无一处未处理异常。
- **涉及模块:** `tests/`（新增测试目录）+ 全部四个源模块（只读验证，不改实现）
- **输入与输出:**
  - 输入：脚本化/手工终端操作序列；预制的合法与损坏 `tasks.json` 夹具
  - 输出：通过的测试报告 / 操作记录
- **具体实现要求:**
  1. 端到端场景（对应 SM-1）：添加 → 查看 → 完成 → 删除 → 统计全链路，断言每步的文件状态与回显。
  2. 持久化场景（SM-2）：添加后杀进程重启，数据完好。
  3. 错误韧性场景（SM-3）：空标题、坏日期、不存在 ID——各有明确提示且程序存活。
  4. **AD-7 专项**：预置损坏文件 → 查看/添加/完成/删除/统计五条路径全部失败返回且文件字节不变（`hashlib` 前后比对）。
  5. **AD-6 专项**：代码审查断言——cli 无裸 except、无 storage import；task_manager 只捕获列明的 storage 异常。
  6. 测试用 unittest（stdlib），放 `tests/` 目录，`python -m unittest discover tests` 一键运行（零依赖原则）。
- **验收标准:**
  - [ ] `python -m unittest discover tests` 全绿。
  - [ ] PRD §8 SM-1 / SM-2 / SM-3 逐条勾验通过。
  - [ ] 损坏文件字节级未被触碰（五路径 × hash 比对）。
- **依赖关系:** S-101 ~ S-304, S-401（全部功能 Story）。
- **对应接口:** 全部公开契约（只调用不修改）

### S-403 · README 与交付打包

- **Story ID:** S-403
- **功能名称:** 交付文档与验证材料（SM-4）
- **用户故事:** 作为课程评估者，我打开 README 就知道如何启动，一张截图证明程序真实可跑。
- **涉及模块:** `README.md`（项目根目录）
- **输入与输出:**
  - 输入：已完成并通过 S-402 的程序
  - 输出：README（真实启动命令、功能说明、目录结构）+ 至少一张运行截图
- **具体实现要求:**
  1. 启动命令必须是**真实可复现**的一条命令（含工作目录前提，如 `cd 项目根目录 && python src/main.py`——与待确认项 3 的路径结论保持一致）。
  2. 简述四模块分层与 `data/tasks.json` 位置；注明 Python 3.9+。
  3. 截图展示主菜单 + 一次成功操作回显。
  4. 不写 pyproject / requirements（脊柱 Deferred：无外部依赖）。
- **验收标准:**
  - [ ] 按 README 原文在一个干净目录 clone 后可一次跑通。
  - [ ] 截图真实（非摆拍代码）、SM-4 勾验通过。
- **依赖关系:** S-402。
- **对应接口:** 无（文档 Story）。

---

## 溯源矩阵（FR/NFR/AD → Story）

| 来源 | 覆盖 Story |
| --- | --- |
| FR-1 / FR-2 | S-202, S-301, S-302, S-201 |
| FR-3 | S-101, S-203, S-303 |
| FR-4 | S-205, S-304 |
| FR-5 | S-203, S-206, S-304 |
| FR-6 | S-204, S-303 |
| FR-7 / FR-8 | S-102, S-301, S-401 |
| NFR 可靠性 | S-101, S-102, S-402（原子写、损坏保护） |
| NFR 可维护性 | 全部（契约钉死）+ S-402 代码审查项 |
| NFR 安全性 | 架构保证（无外部调用），S-402 复核 |
| NFR 易用性 | S-301, S-303, S-304（消息二分落地） |
| AD-1 | S-401, S-402（import 审查） |
| AD-2 | S-201, S-301（校验二分） |
| AD-3 | S-101, S-102 |
| AD-4 | S-202 ~ S-206（现读现写） |
| AD-5 | S-201 |
| AD-6 | S-301（消息二分）, S-402 |
| AD-7 | S-101, S-202, S-402（永不覆写专项） |
