"""S-402 end-to-end integration tests (SM-1..SM-3, AD-7 five-path, OSError).

Run from the project root:
    python -m unittest discover -s tests -v

Restart simulation note: the four modules hold no task state (AD-4), so a
"restart" is simulated by reloading task_manager/cli via importlib between
sessions; the data file on disk is the only carried-over state — exactly as
in a real `python src/main.py` relaunch.
"""

import contextlib
import hashlib
import importlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

import storage  # noqa: E402
import task_manager  # noqa: E402
import cli  # noqa: E402

CORRUPTION_MSG = (
    "Data file is corrupted, unable to read tasks. Please check data/tasks.json."
)
ACCESS_MSG = task_manager._ACCESS_ERROR_MESSAGE


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class IntegrationBase(unittest.TestCase):

    def setUp(self):
        self._orig_dir = storage.DATA_DIR
        self._orig_file = storage.DATA_FILE
        self.sandbox = tempfile.mkdtemp(prefix="quicktask-int-")
        storage.DATA_DIR = os.path.join(self.sandbox, "data")
        storage.DATA_FILE = os.path.join(storage.DATA_DIR, "tasks.json")

    def tearDown(self):
        shutil.rmtree(self.sandbox, ignore_errors=True)
        storage.DATA_DIR = self._orig_dir
        storage.DATA_FILE = self._orig_file

    def run_cli(self, inputs):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=inputs), \
                contextlib.redirect_stdout(out):
            cli.run()
        return out.getvalue()

    def write_data_file(self, tasks):
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False)

    def read_data_file(self):
        with open(storage.DATA_FILE, encoding="utf-8") as f:
            return f.read()

    def simulate_restart(self):
        """Reload modules so only on-disk state carries over (AD-4 proof)."""
        importlib.reload(task_manager)
        importlib.reload(cli)


class TestSM1CreateViewComplete(IntegrationBase):

    def test_sm1_full_create_view_complete_flow(self):
        out = self.run_cli([
            "1", "Prepare Q4 report draft", "Work", "2026-11-15",
            "1", "Reply reviewer comments", "Study", "2026-11-20",
            "2",                      # view: two blocks, both Pending
            "3", "TASK001",           # complete first task
            "2",                      # view: TASK001 Completed
            "6",
        ])
        self.assertIn("Task created successfully! Task ID: TASK001", out)
        self.assertIn("Task created successfully! Task ID: TASK002", out)
        self.assertIn("Status: Pending\n\nTask ID: TASK002", out)
        self.assertIn("Task TASK001 marked as complete!", out)
        self.assertIn("Status: Completed\n\nTask ID: TASK002", out)
        saved = storage.load_tasks()
        self.assertIs(saved[0]["completed"], True)
        self.assertIs(saved[1]["completed"], False)


class TestSM2DeleteAndStatistics(IntegrationBase):

    def test_sm2_delete_updates_statistics(self):
        out = self.run_cli([
            "1", "Keep me", "Work", "2026-11-15",
            "1", "Mistake task", "Work", "2026-11-16",
            "3", "TASK001",           # complete one -> 1 pending, 1 completed
            "4", "TASK002", "y",      # delete the other
            "5",                      # stats: 1 total, 0 pending, 1 done, 100%
            "6",
        ])
        self.assertIn("Task TASK002 deleted successfully!", out)
        self.assertIn("Total: 1", out)
        self.assertIn("Pending: 0", out)
        self.assertIn("Completed: 1", out)
        self.assertIn("Completion rate: 100%", out)
        saved = storage.load_tasks()
        self.assertEqual([t["id"] for t in saved], ["TASK001"])

    def test_delete_then_add_does_not_reuse_id(self):
        self.run_cli(["1", "a", "W", "2026-11-15",
                      "1", "b", "W", "2026-11-16",
                      "4", "TASK001", "y", "6"])
        out = self.run_cli(["1", "fresh", "W", "2026-11-20", "6"])
        self.assertIn("Task ID: TASK003", out)  # TASK002 slot skipped (AD-5)


class TestSM3PersistenceAcrossRestart(IntegrationBase):

    def test_sm3_data_survives_restart(self):
        self.run_cli(["1", "Durable task", "Work", "2026-11-15",
                      "3", "TASK001", "6"])
        self.assertTrue(os.path.isfile(storage.DATA_FILE))
        # Simulate relaunch: modules reloaded, only disk state persists.
        self.simulate_restart()
        out = self.run_cli(["2", "5", "6"])
        self.assertIn("Task ID: TASK001", out)
        self.assertIn("Title: Durable task", out)
        self.assertIn("Status: Completed", out)
        self.assertIn("Total: 1", out)
        self.assertIn("Completion rate: 100%", out)


class TestAD7CorruptFivePaths(IntegrationBase):
    """AD-7: on a corrupt file, five operation paths fail closed and the
    file is never overwritten (hash-verified after each path)."""

    def setUp(self):
        super().setUp()
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            f.write('{"tasks": [')  # corrupt: invalid JSON, non-empty
        self.original_hash = _sha256(storage.DATA_FILE)

    def assert_file_untouched(self):
        self.assertEqual(_sha256(storage.DATA_FILE), self.original_hash)

    def test_path1_view_on_corrupt_file(self):
        out = self.run_cli(["2", "6"])
        self.assertIn(CORRUPTION_MSG, out)
        self.assert_file_untouched()

    def test_path2_add_on_corrupt_file(self):
        out = self.run_cli(["1", "T", "C", "2026-11-15", "6"])
        self.assertIn(CORRUPTION_MSG, out)
        self.assert_file_untouched()

    def test_path3_complete_on_corrupt_file(self):
        out = self.run_cli(["3", "TASK001", "6"])
        self.assertIn(CORRUPTION_MSG, out)
        self.assert_file_untouched()

    def test_path4_delete_on_corrupt_file(self):
        # Pre-check short-circuits ("Task not found."); write path never
        # reached; file untouched. [documented behavior, user-approved Q4]
        out = self.run_cli(["4", "TASK001", "6"])
        self.assertIn("Task not found.", out)
        self.assertNotIn("Are you sure", out)
        self.assert_file_untouched()

    def test_path5_statistics_on_corrupt_file(self):
        out = self.run_cli(["5", "6"])
        self.assertIn(CORRUPTION_MSG, out)
        self.assert_file_untouched()

    def test_all_five_paths_sequentially_never_repair_or_overwrite(self):
        self.run_cli(["2", "1", "T", "C", "2026-11-15", "3", "TASK001",
                      "4", "TASK001", "5", "6"])
        self.assert_file_untouched()
        self.assertEqual(self.read_data_file(), '{"tasks": [')


class TestFileAccessErrors(IntegrationBase):
    """PermissionError / OSError scenarios (AD-6 boundary)."""

    def test_load_permission_error_shows_message_no_crash(self):
        with mock.patch.object(storage, "load_tasks",
                               side_effect=PermissionError("locked")), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            with mock.patch("builtins.input", side_effect=["2", "6"]):
                cli.run()
        self.assertIn(ACCESS_MSG, out.getvalue())

    def test_add_with_unreadable_file_fails_gracefully(self):
        with mock.patch.object(storage, "load_tasks",
                               side_effect=PermissionError("locked")):
            result = task_manager.add_task("T", "C", "2026-11-15")
        self.assertEqual(result, (False, ACCESS_MSG, None))

    def test_save_permission_error_preserves_original_and_reports(self):
        self.run_cli(["1", "Original", "W", "2026-11-15", "6"])
        before = _sha256(storage.DATA_FILE)
        with mock.patch.object(storage, "save_tasks",
                               side_effect=PermissionError("locked")):
            result = task_manager.add_task("Second", "W", "2026-11-16")
        self.assertEqual(result, (False, ACCESS_MSG, None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)  # original kept

    def test_atomic_write_failure_preserves_original_end_to_end(self):
        # Integration-level re-verification of the wave-1 atomicity test.
        # Real "disk full" manifests as OSError -> AD-6 failure tuple.
        self.run_cli(["1", "First", "W", "2026-11-15", "6"])
        before = _sha256(storage.DATA_FILE)
        with mock.patch.object(storage.json, "dump",
                               side_effect=OSError(28, "No space left")):
            result = task_manager.add_task("Second", "W", "2026-11-16")
        self.assertEqual(result, (False, ACCESS_MSG, None))
        self.assertEqual(_sha256(storage.DATA_FILE), before)
        leftovers = [n for n in os.listdir(storage.DATA_DIR)
                     if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_non_oserror_during_save_propagates_but_file_stays_intact(self):
        # An unexpected (non-storage-boundary) exception is allowed to
        # propagate per AD-6's exception list — but atomicity (AD-3) must
        # still hold: original file intact, no temp residue.
        self.run_cli(["1", "First", "W", "2026-11-15", "6"])
        before = _sha256(storage.DATA_FILE)
        with mock.patch.object(storage.json, "dump",
                               side_effect=RuntimeError("simulated crash")):
            with self.assertRaises(RuntimeError):
                task_manager.add_task("Second", "W", "2026-11-16")
        self.assertEqual(_sha256(storage.DATA_FILE), before)
        leftovers = [n for n in os.listdir(storage.DATA_DIR)
                     if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
