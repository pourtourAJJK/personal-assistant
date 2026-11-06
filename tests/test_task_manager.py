"""S-201..S-206 acceptance tests for task_manager.py.

Run from the project root:
    python -m unittest discover -s tests -v

Contracts verified verbatim against ARCHITECTURE-SPINE.md Rev-2.
Wave-1 regression (tests/test_storage.py) runs in the same discovery.
"""

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

import storage  # noqa: E402
import task_manager  # noqa: E402

CORRUPTION_MSG = (
    "Data file is corrupted, unable to read tasks. Please check data/tasks.json."
)
CREATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def make_task(task_id, title="Sample", completed=False):
    return {"id": task_id, "title": title, "category": "Work",
            "due_date": "2026-11-15", "completed": completed,
            "created_at": "2026-11-06T10:00:00"}


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TaskManagerTestBase(unittest.TestCase):
    """Redirect storage paths to a temp sandbox (same approach as wave 1)."""

    def setUp(self):
        self._orig_dir = storage.DATA_DIR
        self._orig_file = storage.DATA_FILE
        self.sandbox = tempfile.mkdtemp(prefix="quicktask-tm-")
        storage.DATA_DIR = os.path.join(self.sandbox, "data")
        storage.DATA_FILE = os.path.join(storage.DATA_DIR, "tasks.json")

    def tearDown(self):
        shutil.rmtree(self.sandbox, ignore_errors=True)
        storage.DATA_DIR = self._orig_dir
        storage.DATA_FILE = self._orig_file

    def write_data_file(self, tasks):
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False)

    def write_corrupt_file(self):
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            f.write("{not valid json]]")

    def saved_tasks(self):
        return storage.load_tasks()


class TestS201GenerateTaskId(TaskManagerTestBase):

    def test_empty_list_gives_task001(self):
        self.assertEqual(task_manager.generate_task_id([]), "TASK001")

    def test_max_plus_one(self):
        tasks = [make_task("TASK001"), make_task("TASK002")]
        self.assertEqual(task_manager.generate_task_id(tasks), "TASK003")

    def test_gap_after_deletion_not_reused(self):
        # TASK003 was deleted; remaining max is TASK004 -> next TASK005.
        tasks = [make_task("TASK001"), make_task("TASK002"),
                 make_task("TASK004")]
        self.assertEqual(task_manager.generate_task_id(tasks), "TASK005")

    def test_overflow_beyond_999_grows_naturally(self):
        tasks = [make_task("TASK999")]
        self.assertEqual(task_manager.generate_task_id(tasks), "TASK1000")

    def test_malformed_and_missing_ids_are_skipped(self):
        tasks = [
            {"title": "no id"},                # missing id
            {"id": "junk", "title": "bad"},    # malformed id
            {"id": "TASKXYZ", "title": "bad"}, # non-numeric suffix
            "not-a-dict",                      # non-dict entry
            make_task("TASK002"),
        ]
        self.assertEqual(task_manager.generate_task_id(tasks), "TASK003")

    def test_zero_padding_minimum_three_digits(self):
        self.assertEqual(len(task_manager.generate_task_id([])) - 4, 3)


class TestS201BuildTask(TaskManagerTestBase):

    def test_build_valid_task_shape(self):
        task = task_manager._build_task("写周报", "工作", "2026-11-15", "TASK001")
        self.assertEqual(set(task.keys()),
                         {"id", "title", "category", "due_date",
                          "completed", "created_at"})
        self.assertEqual(task["id"], "TASK001")
        self.assertIs(task["completed"], False)
        self.assertRegex(task["created_at"], CREATED_AT_RE)
        self.assertNotIn(".", task["created_at"])  # no microseconds (AD-2)

    def test_build_rejects_empty_title_and_category(self):
        self.assertIsNone(task_manager._build_task("  ", "Work",
                                                   "2026-11-15", "TASK001"))
        self.assertIsNone(task_manager._build_task("T", "",
                                                   "2026-11-15", "TASK001"))

    def test_build_rejects_bad_dates(self):
        for bad in ("2026-13-45", "2026/11/15", "", None, "not-a-date"):
            self.assertIsNone(task_manager._build_task("T", "C", bad,
                                                       "TASK001"))

    def test_build_allows_past_date(self):
        # PRD §9 Q3: past due dates are allowed.
        self.assertIsNotNone(task_manager._build_task("T", "C",
                                                      "2020-01-01", "TASK001"))


class TestS202AddTask(TaskManagerTestBase):

    def test_add_success_returns_tuple_with_new_id(self):
        ok, msg, new_id = task_manager.add_task("Prepare Q4 report draft",
                                                "Work", "2026-11-15")
        self.assertTrue(ok)
        self.assertEqual(new_id, "TASK001")
        self.assertEqual(msg, "Task created successfully! "
                              "Task ID: TASK001, Task title: Prepare Q4 report draft")

    def test_add_persists_full_entity_immediately(self):
        task_manager.add_task("写周报", "工作", "2026-11-15")
        saved = self.saved_tasks()
        self.assertEqual(len(saved), 1)
        task = saved[0]
        self.assertEqual(task["id"], "TASK001")
        self.assertEqual(task["title"], "写周报")
        self.assertEqual(task["category"], "工作")
        self.assertEqual(task["due_date"], "2026-11-15")
        self.assertIs(task["completed"], False)
        self.assertRegex(task["created_at"], CREATED_AT_RE)

    def test_sequential_adds_get_sequential_ids(self):
        for i, title in enumerate(["a", "b", "c"], start=1):
            ok, _, new_id = task_manager.add_task(title, "Work",
                                                  "2026-11-20")
            self.assertTrue(ok)
            self.assertEqual(new_id, "TASK%03d" % i)
        self.assertEqual(len(self.saved_tasks()), 3)

    def test_add_on_corrupt_file_fails_without_saving(self):
        self.write_corrupt_file()
        before = _sha256(storage.DATA_FILE)
        ok, msg, data = task_manager.add_task("T", "C", "2026-11-15")
        self.assertFalse(ok)
        self.assertEqual(msg, CORRUPTION_MSG)
        self.assertIsNone(data)
        # AD-7: corrupt file never overwritten.
        self.assertEqual(_sha256(storage.DATA_FILE), before)

    def test_add_invalid_entity_fails_without_saving(self):
        ok, msg, data = task_manager.add_task("T", "C", "2026-13-45")
        self.assertFalse(ok)
        self.assertEqual(msg, task_manager._INVALID_TASK_MESSAGE)
        self.assertIsNone(data)
        self.assertFalse(os.path.exists(storage.DATA_FILE))  # nothing saved


class TestS203ViewAndGetTask(TaskManagerTestBase):

    def test_view_empty_returns_true_with_empty_list(self):
        self.assertEqual(task_manager.view_tasks(), (True, "", []))

    def test_view_missing_file_returns_true_with_empty_list(self):
        self.assertEqual(task_manager.view_tasks(), (True, "", []))

    def test_view_returns_all_tasks_in_order(self):
        tasks = [make_task("TASK001", "first"), make_task("TASK002", "second")]
        self.write_data_file(tasks)
        ok, msg, data = task_manager.view_tasks()
        self.assertTrue(ok)
        self.assertEqual(msg, "")
        self.assertEqual(data, tasks)

    def test_view_corrupt_fails_without_modifying_file(self):
        self.write_corrupt_file()
        before = _sha256(storage.DATA_FILE)
        self.assertEqual(task_manager.view_tasks(),
                         (False, CORRUPTION_MSG, None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)

    def test_get_task_found_returns_dict(self):
        tasks = [make_task("TASK001", "alpha"), make_task("TASK002", "beta")]
        self.write_data_file(tasks)
        self.assertEqual(task_manager.get_task("TASK002"),
                         make_task("TASK002", "beta"))

    def test_get_task_not_found_returns_none(self):
        self.write_data_file([make_task("TASK001")])
        self.assertIsNone(task_manager.get_task("TASK999"))

    def test_get_task_corrupt_returns_none_per_contract(self):
        # Contract: dict | None — no exception path. Delete's second-layer
        # protection (delete_task result tuple) still guards corruption.
        self.write_corrupt_file()
        self.assertIsNone(task_manager.get_task("TASK001"))

    def test_no_cache_sees_external_file_changes(self):
        # AD-4: every operation loads fresh; no module-level list.
        task_manager.add_task("one", "W", "2026-11-15")
        external = self.saved_tasks() + [make_task("TASK099", "injected")]
        self.write_data_file(external)
        _, _, data = task_manager.view_tasks()
        self.assertEqual([t["id"] for t in data], ["TASK001", "TASK099"])


class TestS204GetStatistics(TaskManagerTestBase):

    def test_statistics_matches_prd_uj5(self):
        tasks = [make_task("TASK%03d" % i, completed=(i <= 4))
                 for i in range(1, 11)]
        self.write_data_file(tasks)
        ok, msg, stats = task_manager.get_statistics()
        self.assertTrue(ok)
        self.assertEqual(msg, "")
        self.assertEqual(stats, {"total": 10, "pending": 6, "completed": 4,
                                 "completion_rate": 40})

    def test_statistics_empty_is_all_zeros_no_division_error(self):
        self.assertEqual(task_manager.get_statistics(),
                         (True, "", {"total": 0, "pending": 0, "completed": 0,
                                     "completion_rate": 0}))

    def test_statistics_missing_file_is_all_zeros(self):
        self.assertEqual(task_manager.get_statistics()[1:], 
                         ("", {"total": 0, "pending": 0, "completed": 0,
                               "completion_rate": 0}))

    def test_statistics_rounds_to_nearest_int(self):
        tasks = [make_task("TASK001"), make_task("TASK002"),
                 make_task("TASK003", completed=True)]
        self.write_data_file(tasks)  # 1/3 = 33.33% -> 33
        self.assertEqual(task_manager.get_statistics()[2]["completion_rate"], 33)

    def test_statistics_corrupt_fails_without_modifying_file(self):
        self.write_corrupt_file()
        before = _sha256(storage.DATA_FILE)
        self.assertEqual(task_manager.get_statistics(),
                         (False, CORRUPTION_MSG, None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)


class TestS205CompleteTask(TaskManagerTestBase):

    def test_complete_success_flips_bool_and_persists(self):
        self.write_data_file([make_task("TASK001"), make_task("TASK002")])
        before = _sha256(storage.DATA_FILE)
        ok, msg, data = task_manager.complete_task("TASK001")
        self.assertEqual((ok, msg, data),
                         (True, "Task TASK001 marked as complete!", None))
        saved = self.saved_tasks()
        self.assertIs(saved[0]["completed"], True)  # real bool, not "true"
        self.assertIs(saved[1]["completed"], False)  # others untouched
        self.assertNotEqual(_sha256(storage.DATA_FILE), before)  # saved

    def test_complete_already_completed_is_idempotent_success(self):
        self.write_data_file([make_task("TASK001", completed=True)])
        before = _sha256(storage.DATA_FILE)
        self.assertEqual(task_manager.complete_task("TASK001"),
                         (True, "Task TASK001 is already completed.", None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)  # file untouched

    def test_complete_not_found_fails_with_prd_message(self):
        self.write_data_file([make_task("TASK001")])
        before = _sha256(storage.DATA_FILE)
        self.assertEqual(task_manager.complete_task("TASK999"),
                         (False, "Task not found, please check the Task ID.",
                          None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)

    def test_complete_corrupt_fails_without_saving(self):
        self.write_corrupt_file()
        before = _sha256(storage.DATA_FILE)
        self.assertEqual(task_manager.complete_task("TASK001"),
                         (False, CORRUPTION_MSG, None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)  # AD-7


class TestS206DeleteTask(TaskManagerTestBase):

    def test_delete_success_removes_exactly_one(self):
        tasks = [make_task("TASK001", "keep"), make_task("TASK002", "gone"),
                 make_task("TASK003", "keep too")]
        self.write_data_file(tasks)
        ok, msg, data = task_manager.delete_task("TASK002")
        self.assertEqual((ok, msg, data),
                         (True, "Task TASK002 deleted successfully!", None))
        saved = self.saved_tasks()
        self.assertEqual([t["id"] for t in saved], ["TASK001", "TASK003"])
        self.assertEqual(saved[0], tasks[0])   # byte-equal survivors
        self.assertEqual(saved[1], tasks[2])

    def test_delete_then_add_does_not_reuse_id(self):
        self.write_data_file([make_task("TASK001"), make_task("TASK002"),
                              make_task("TASK003")])
        task_manager.delete_task("TASK002")
        ok, _, new_id = task_manager.add_task("fresh", "W", "2026-11-15")
        self.assertTrue(ok)
        self.assertEqual(new_id, "TASK004")  # AD-5: never reuse

    def test_delete_not_found_fails_with_prd_message(self):
        self.write_data_file([make_task("TASK001")])
        before = _sha256(storage.DATA_FILE)
        self.assertEqual(task_manager.delete_task("TASK999"),
                         (False, "Task not found.", None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)

    def test_delete_corrupt_fails_without_saving(self):
        self.write_corrupt_file()
        before = _sha256(storage.DATA_FILE)
        self.assertEqual(task_manager.delete_task("TASK001"),
                         (False, CORRUPTION_MSG, None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)  # AD-7


if __name__ == "__main__":
    unittest.main()
