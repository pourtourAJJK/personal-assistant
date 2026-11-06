"""S-101 / S-102 acceptance tests for storage.py.

Run from the project root:
    python -m unittest discover -s tests -v

Covers (per DEVELOPMENT-PLAN.md wave 1 gate):
    - load: missing file / missing dir / 0-byte / whitespace / valid / corrupt JSON / non-array root
    - save: round-trip (UTF-8, Chinese, ensure_ascii=False), dir lazy-creation,
      overwrite, no temp residue, failure preserves original (atomicity)
    - path base: data/tasks.json anchored at project root regardless of CWD
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

# Make src/ importable regardless of where the test runner is invoked from.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

import storage  # noqa: E402


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class StorageTestBase(unittest.TestCase):
    """Redirect storage's module-level path constants to a temp sandbox."""

    def setUp(self):
        self._orig_dir = storage.DATA_DIR
        self._orig_file = storage.DATA_FILE
        self.sandbox = tempfile.mkdtemp(prefix="quicktask-test-")
        storage.DATA_DIR = os.path.join(self.sandbox, "data")
        storage.DATA_FILE = os.path.join(storage.DATA_DIR, "tasks.json")

    def tearDown(self):
        shutil.rmtree(self.sandbox, ignore_errors=True)
        storage.DATA_DIR = self._orig_dir
        storage.DATA_FILE = self._orig_file

    # -- helpers ---------------------------------------------------------

    def write_data_file(self, content):
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            f.write(content)


class TestLoadTasks(StorageTestBase):

    def test_load_missing_file_returns_empty_list(self):
        # Neither data/ nor tasks.json exists.
        self.assertEqual(storage.load_tasks(), [])

    def test_load_missing_dir_returns_empty_list(self):
        # data/ does not exist at all (same observable case, explicit).
        self.assertFalse(os.path.exists(storage.DATA_DIR))
        self.assertEqual(storage.load_tasks(), [])

    def test_load_zero_byte_file_returns_empty_list(self):
        self.write_data_file("")
        self.assertEqual(storage.load_tasks(), [])

    def test_load_whitespace_file_returns_empty_list(self):
        self.write_data_file("   \n\t ")
        self.assertEqual(storage.load_tasks(), [])

    def test_load_valid_tasks_returns_list_in_order(self):
        tasks = [
            {"id": "TASK001", "title": "Prepare Q4 report draft",
             "category": "Work", "due_date": "2026-11-15",
             "completed": False, "created_at": "2026-11-06T10:00:00"},
            {"id": "TASK002", "title": "团队周会",
             "category": "Meeting", "due_date": "2026-11-07",
             "completed": True, "created_at": "2026-11-06T11:00:00"},
        ]
        self.write_data_file(json.dumps(tasks, ensure_ascii=False))
        result = storage.load_tasks()
        self.assertEqual(result, tasks)
        self.assertEqual([t["id"] for t in result], ["TASK001", "TASK002"])

    def test_load_corrupt_json_raises_jsondecodeerror(self):
        self.write_data_file("{not valid json]]")
        before = _sha256(storage.DATA_FILE)
        with self.assertRaises(json.JSONDecodeError):
            storage.load_tasks()
        # AD-7: read path never mutates the file.
        self.assertEqual(_sha256(storage.DATA_FILE), before)

    def test_load_root_not_array_raises_valueerror(self):
        self.write_data_file('{"id": "TASK001"}')
        before = _sha256(storage.DATA_FILE)
        with self.assertRaises(ValueError):
            storage.load_tasks()
        self.assertEqual(_sha256(storage.DATA_FILE), before)


class TestSaveTasks(StorageTestBase):

    def test_save_creates_missing_dir_lazily(self):
        # PRD FR-7 vs AD-3 [USER-APPROVED]: dir created on first save only.
        self.assertFalse(os.path.exists(storage.DATA_DIR))
        storage.save_tasks([])
        self.assertTrue(os.path.isdir(storage.DATA_DIR))
        self.assertTrue(os.path.isfile(storage.DATA_FILE))

    def test_save_load_roundtrip_preserves_chinese_and_order(self):
        tasks = [
            {"id": "TASK001", "title": "准备季度报告初稿",
             "category": "工作", "due_date": "2026-11-15",
             "completed": False, "created_at": "2026-11-06T10:00:00"},
            {"id": "TASK002", "title": "Reply reviews",
             "category": "Study", "due_date": "2026-11-20",
             "completed": True, "created_at": "2026-11-06T12:30:00"},
        ]
        storage.save_tasks(tasks)
        self.assertEqual(storage.load_tasks(), tasks)

    def test_save_file_is_human_readable_utf8_no_ascii_escaping(self):
        tasks = [{"id": "TASK001", "title": "中文任务", "category": "工作",
                  "due_date": "2026-11-15", "completed": False,
                  "created_at": "2026-11-06T10:00:00"}]
        storage.save_tasks(tasks)
        with open(storage.DATA_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        self.assertIn("中文任务", raw)  # ensure_ascii=False: not \uXXXX escaped
        self.assertIn('"due_date"', raw)  # indent=2: human-readable layout

    def test_save_overwrites_existing_content(self):
        storage.save_tasks([{"id": "TASK001"}])
        storage.save_tasks([{"id": "TASK001"}, {"id": "TASK002"}])
        self.assertEqual(len(storage.load_tasks()), 2)

    def test_save_leaves_no_temp_file_residue(self):
        storage.save_tasks([])
        leftovers = [n for n in os.listdir(storage.DATA_DIR)
                     if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_save_failure_preserves_original_file(self):
        original = [{"id": "TASK001", "title": "keep me", "category": "w",
                     "due_date": "2026-11-15", "completed": False,
                     "created_at": "2026-11-06T10:00:00"}]
        storage.save_tasks(original)
        before = _sha256(storage.DATA_FILE)
        with mock.patch.object(storage.json, "dump",
                               side_effect=RuntimeError("simulated crash")):
            with self.assertRaises(RuntimeError):
                storage.save_tasks([{"id": "TASK002"}])
        # AD-3 atomicity: target untouched on failure.
        self.assertEqual(_sha256(storage.DATA_FILE), before)
        # No temp residue after failure either.
        leftovers = [n for n in os.listdir(storage.DATA_DIR)
                     if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])


class TestPathBase(unittest.TestCase):
    """Verify module constants directly — no sandbox redirection."""

    def test_data_file_anchored_at_project_root(self):
        # [USER-APPROVED Q2]: <project_root>/data/tasks.json via __file__.
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(storage.__file__))
        )
        expected = os.path.join(project_root, "data", "tasks.json")
        self.assertEqual(os.path.abspath(storage.DATA_FILE),
                         os.path.abspath(expected))
        self.assertTrue(os.path.isabs(storage.DATA_FILE))

    def test_load_uses_anchored_path_not_cwd(self):
        # Prove the CWD is irrelevant: from a foreign cwd, load_tasks()
        # still resolves against the anchored project-root path (which does
        # not exist in a fresh checkout → []), not against ./data/tasks.json.
        cwd = os.getcwd()
        foreign = tempfile.mkdtemp(prefix="quicktask-cwd-")
        try:
            os.chdir(foreign)
            self.assertEqual(storage.load_tasks(), [])
            self.assertFalse(os.path.exists(
                os.path.join(foreign, "data", "tasks.json")))
        finally:
            os.chdir(cwd)
            shutil.rmtree(foreign, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
