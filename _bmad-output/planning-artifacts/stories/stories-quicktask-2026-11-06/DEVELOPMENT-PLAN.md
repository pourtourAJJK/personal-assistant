---
name: QuickTask V1 Development Plan
type: development-plan
purpose: build-guidance
sources: [stories-quicktask-2026-11-06, architecture-personal-assistant-2026-11-06 (Rev-2 spine)]
status: draft
created: 2026-11-06
updated: 2026-11-06
---

# QuickTask V1 — 开发任务规划

## 1. 实施顺序（依赖驱动的五个波次）

```text
波次1  S-101 load_tasks ──→ S-102 save_tasks          [E1 存储基座]
              │
波次2  S-201 ID/实体 ──┬→ S-202 add_task               [E2 业务核心]
              ├→ S-203 view+get_task（与 S-202 并行）
              ├→ S-204 statistics（并行）
              ├→ S-205 complete_task（并行）
              └→ S-206 delete_task（并行）
                        │
波次3  S-301 菜单+校验框架 ──┬→ S-302 添加流           [E3 交互层]
                            ├→ S-303 查看/统计流（并行）
                            └→ S-304 完成/删除流（并行）
                                      │
波次4  S-401 main.py 入口                                   [E4 组装]
                        │
波次5  S-402 集成测试+异常专项 ──→ S-403 README+交付
```

| 波次 | Stories | 波次验收门槛（未过不进下一波） |
| --- | --- | --- |
| 1 | S-101, S-102 | 四态读取语义 + 原子写 round-trip 单测全绿 |
| 2 | S-201 → S-202/S-203/S-204/S-205/S-206 | 每个公开函数契约测试通过；损坏文件下所有写路径证明不落盘 |
| 3 | S-301 → S-302/S-303/S-304 | 六项菜单循环可走通；PRD 固定文案逐字比对通过；cli 无越层 import |
| 4 | S-401 | 全新目录一键启动、首次保存建目录、重启数据完好 |
| 5 | S-402 → S-403 | SM-1~SM-3 全过 + 损坏文件五路径 hash 不变 → SM-4 交付 |

**并行说明：** 波次 2 内 S-203~S-206 相互独立可并行（同一文件 `task_manager.py`，单人开发则按编号串行）；波次 3 同理。

## 2. 按模块的文件清单与职责边界

| 文件 | 波次 | 承载 Story | 职责（严格等于脊柱分层） | 明确不做 |
| --- | --- | --- | --- | --- |
| `src/storage.py` | 1 | S-101, S-102 | load 四态语义、原子写、UTF-8、路径常量、损坏检测抛异常 | 不写消息文案、不理解 Task 字段含义 |
| `src/task_manager.py` | 2 | S-201~S-206 | 现读现写 CRUD、ID 生成、实体构造与防御校验、统计、结果元组与操作结果文案 | 不 import json/os 触碰数据文件、不 print、不做输入重试 |
| `src/cli.py` | 3 | S-301~S-304 | 菜单循环、原始输入校验重试、结果展示、列表/统计渲染、删除确认 | 不 try/except storage 异常、不定义操作结果文案、不 import json |
| `src/main.py` | 4 | S-401 | `main() -> cli.run()`，仅此而已 | 不做初始化、不 import cli 之外的项目模块 |
| `tests/`（新目录） | 5（随各波次增补） | S-402 汇总 | 四态/契约/端到端/损坏专项测试 | 不引入 pytest 等外部框架 |
| `README.md` | 5 | S-403 | 启动命令、结构说明、截图 | 不写安装依赖步骤（无依赖） |

运行期产物：`data/tasks.json`（首次保存时由 S-102 创建，不入版本库，建议加 `.gitignore`）。

## 3. 测试策略

- **框架：** `unittest`（stdlib），零依赖，符合脊柱 Deferred 的"per-story decision"——本规划将其定为全项目统一选择。
- **层级：**
  1. **单元层**（波次 1–2）：storage 四态、ID 契约、各业务函数的成功/失败/损坏三路返回值——直接断言元组形状与 data 字段类型。
  2. **交互层**（波次 3）：校验辅助函数纯函数测试；菜单文案与 PRD 逐字比对。
  3. **端到端层**（波次 5）：SM-1/2/3 场景 + AD-7 五路径损坏不覆写专项（hash 比对）+ AD-6 静态审查项。
- **夹具：** `tests/fixtures/` 预置合法（含中文）、空文件、损坏 JSON、根非数组四种 `tasks.json`。

## 4. 需要总裁确认的问题（阻塞项标 ⚠）

1. **⚠ PRD FR-7 与脊柱 AD-3 的措辞差异：** PRD 写「启动时若 data/tasks.json 不存在则创建 data/ 目录并初始化空列表」；脊柱 Rev-2 定为**懒初始化**——启动不建目录，首次保存（第一条 Add）时才创建。行为差异仅在"运行过但从未添加过任务时 data/ 目录是否存在"。**建议：以脊柱为准**（无副作用读取更干净，且 PRD 的实质意图"不崩溃"完全满足）。确认后如需严格对齐 PRD，可在 S-401 加一行初始化调用——但那需要改脊柱 AD-3，请明示。
2. **⚠ 数据文件路径基准：** 脊柱 AD-3 说路径常量在 storage.py 内，但未钉死是相对 CWD 还是相对源码位置。`python src/main.py` 从项目根运行时相对路径 `data/tasks.json` 可行，但换目录启动会在别处建 `data/`。**建议：以项目根为基准解析**（`storage.py` 内由 `__file__` 向上定位），对用户透明、不怕启动目录漂移。这属于 AD-3 的实现细化而非接口变更，但请确认。
3. **tests/ 目录：** 脊柱 Structural Seed 未含 tests/。规划新增 `tests/`（纯增量，不触碰四模块依赖关系，不违反任何 AD）。如要求结构种子零改动可改为 `src/` 内测试文件——不推荐。默认按新增 `tests/` 执行。
4. **complete_task 幂等语义：** 脊柱已钉死"已完成 → success=True + already completed 信息文案"。PRD 未规定 success 取值。脊柱为准，无需动作，报备知悉。
5. **删除确认 not-found 分支：** S-304 中 cli 先用 `get_task` 判空显示 "Task not found."（不进入确认、不调 delete_task）。PRD 文案一致，但该分支文案在 cli 显示——是否允许 cli 在此分支直接输出 PRD 文案？**建议：允许**（这是交互前置判断，属 cli 交互消息集；task_manager 的 delete_task 自身 not-found 文案仍按契约存在，双保险）。

## 5. 风险与红线

- **红线 1：** 任何 Story 不得改动脊柱 Interface Contracts 的签名、结果元组形状、消息归属二分——发现做不到时停下来上报，不静默改契约。
- **红线 2：** 损坏文件场景下任何写路径触达 `save_tasks()` 即为最高优先级缺陷（AD-7 破防，数据毁灭级）。
- **红线 3：** 不引入任何外部依赖；`requirements.txt` / `pyproject.toml` 不出现。
- **已知风险：** `os.replace` 在 Windows 上目标被占用（如用户用编辑器锁住 tasks.json）会抛 `PermissionError`——AD-6 已把 `PermissionError` 列入 storage 异常集，task_manager 转失败元组即可，无需额外处理；列入 S-402 错误韧性场景。
