# QuickTask — 命令行任务管理工具

QuickTask 是一个轻量的本地任务管理工具：在终端中添加、查看、完成、删除任务，并查看统计摘要。数据保存在本地 JSON 文件中，无需安装任何第三方依赖——只需要 Python 3.9+。

## 功能（V1）

| 菜单 | 功能 | 说明 |
| --- | --- | --- |
| 1 | Add Task | 输入标题、分类、截止日期（YYYY-MM-DD），自动生成唯一 ID（TASK001 起）并立即持久化 |
| 2 | View Tasks | 逐条显示全部任务（ID / 标题 / 分类 / 截止日期 / 状态） |
| 3 | Complete Task | 按 ID 标记完成；重复标记给出友好提示 |
| 4 | Delete Task | 按 ID 删除，先展示详情再确认，防止误删 |
| 5 | Task Statistics | 总数 / 待办 / 已完成 / 完成率 |
| 6 | Exit | 干净退出（每步操作已即时保存，无丢失风险） |

可靠性保证：数据文件损坏时所有操作安全失败且**永不覆盖原文件**；每次保存为原子替换（临时文件 + rename），程序崩溃不会留下半个文件。

## 技术栈

- Python 3.9+（仅标准库：`json`、`os`、`datetime`、`tempfile`、`re`、`unittest`）
- 无任何第三方依赖，无数据库，无网络调用，无账号体系
- 分层架构：`storage.py`（数据访问）→ `task_manager.py`（业务逻辑）→ `cli.py`（终端交互）→ `main.py`（入口），依赖严格单向向下，便于未来迁移到 Web 架构

## 目录结构

```text
personal-assistant/
├── README.md            # 本文件
├── .gitignore
├── src/
│   ├── main.py          # 入口：main() -> cli.run()
│   ├── cli.py           # 菜单循环、输入校验、结果展示
│   ├── task_manager.py  # 任务 CRUD、ID 生成、统计、结果元组
│   └── storage.py       # JSON 读写、目录懒创建、原子写、损坏检测
├── tests/               # unittest 测试（5 个文件，97 个用例）
└── data/
    └── tasks.json       # 运行时自动创建（首次保存任务时），UTF-8
```

## 环境要求

- Python 3.9 或更高版本（`python --version` 确认）
- 无需安装任何包

## 运行方式

```bash
cd personal-assistant          # 项目根目录
python src/main.py
```

首次运行无需任何准备步骤：`data/` 目录会在你添加第一条任务时自动创建。

## 运行测试

```bash
cd personal-assistant
python -m unittest discover -s tests -v
```

测试覆盖：读取四态语义（缺失/空/正常/损坏）、原子写与失败保留原文件、ID 生成契约、五个业务函数的结果元组、CLI 交互流（含校验重试与删除确认）、端到端场景（创建-查看-完成、删除-统计、重启恢复）、损坏文件五路径不覆写专项、文件访问异常韧性。

## 数据说明

- 数据文件：`data/tasks.json`，UTF-8 编码，JSON 数组，可直接用文本编辑器查看
- 任务字段：`id`、`title`、`category`、`due_date`（YYYY-MM-DD）、`completed`（布尔）、`created_at`
- 删除任务后 ID 不复用（删掉 TASK003 后新建任务仍是 TASK004）
- 过去的截止日期允许录入（便于补录）
