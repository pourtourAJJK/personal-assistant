"""S-301..S-304 acceptance tests for cli.py.

Run from the project root:
    python -m unittest discover -s tests -v

Strategy: patch builtins.input with scripted sequences and capture stdout;
mutate the real data file through storage (sandboxed) to drive each flow.
Static AD checks (no json import, no bare except) included.
"""

import contextlib
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


def make_task(task_id, title="Sample", completed=False):
    return {"id": task_id, "title": title, "category": "Work",
            "due_date": "2026-11-15", "completed": completed,
            "created_at": "2026-11-06T10:00:00"}


class CliTestBase(unittest.TestCase):

    def setUp(self):
        self._orig_dir = storage.DATA_DIR
        self._orig_file = storage.DATA_FILE
        self.sandbox = tempfile.mkdtemp(prefix="quicktask-cli-")
        storage.DATA_DIR = os.path.join(self.sandbox, "data")
        storage.DATA_FILE = os.path.join(storage.DATA_DIR, "tasks.json")

    def tearDown(self):
        shutil.rmtree(self.sandbox, ignore_errors=True)
        storage.DATA_DIR = self._orig_dir
        storage.DATA_FILE = self._orig_file

    def run_cli(self, inputs):
        """Run cli.run() with scripted stdin; return captured stdout."""
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=inputs), \
                contextlib.redirect_stdout(out):
            cli.run()
        return out.getvalue()

    def saved_tasks(self):
        return storage.load_tasks()


class TestS301ValidationHelpers(CliTestBase):

    def test_title_reprompts_until_nonempty(self):
        with mock.patch("builtins.input",
                        side_effect=["", "   ", "Real title"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli._prompt_title(), "Real title")
        self.assertEqual(out.getvalue().count(
            "Task title cannot be empty, please re-enter."), 2)

    def test_category_reprompts_until_nonempty(self):
        with mock.patch("builtins.input",
                        side_effect=["", "Work"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli._prompt_category(), "Work")
        self.assertIn("Task category cannot be empty, please re-enter.",
                      out.getvalue())

    def test_date_bad_shape_gets_format_message(self):
        with mock.patch("builtins.input",
                        side_effect=["2026/11/15", "15-11-2026",
                                     "2026-11-15"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli._prompt_due_date(), "2026-11-15")
        output = out.getvalue()
        self.assertEqual(output.count(
            "Invalid date format, please use YYYY-MM-DD."), 2)
        self.assertNotIn("Invalid date value", output)

    def test_date_bad_value_gets_value_message(self):
        with mock.patch("builtins.input",
                        side_effect=["2026-13-45", "2026-02-30",
                                     "2026-11-15"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli._prompt_due_date(), "2026-11-15")
        output = out.getvalue()
        self.assertEqual(output.count(
            "Invalid date value, please check the date."), 2)
        self.assertNotIn("Invalid date format", output)

    def test_past_date_is_allowed(self):
        with mock.patch("builtins.input", side_effect=["2020-01-01"]):
            self.assertEqual(cli._prompt_due_date(), "2020-01-01")

    def test_menu_loop_invalid_option_then_exit(self):
        output = self.run_cli(["0", "abc", "9", "6"])
        self.assertIn("Invalid option, please enter a number from 1 to 6.",
                      output)
        self.assertEqual(output.count("QuickTask - Task Manager"), 4)

    def test_menu_dispatches_actions_and_returns_to_menu(self):
        # 1 -> add flow, then 2 -> view shows the created task, then exit.
        output = self.run_cli(["1", "T", "C", "2026-11-15", "2", "6"])
        self.assertIn("Task created successfully", output)
        self.assertIn("Task ID: TASK001", output)
        # Menu redisplayed after each operation (PRD FR-7).
        self.assertGreaterEqual(output.count("QuickTask - Task Manager"), 3)

    def test_menu_exit_stops_loop(self):
        output = self.run_cli(["6"])
        self.assertEqual(output.count("QuickTask - Task Manager"), 1)
        self.assertEqual(len(self.saved_tasks()), 0)  # clean exit, no writes


class TestS302AddFlow(CliTestBase):

    def test_add_flow_full_success(self):
        output = self.run_cli(["1", "Prepare Q4 report draft", "Work",
                               "2026-11-15", "6"])
        self.assertIn("Task created successfully! Task ID: TASK001, "
                      "Task title: Prepare Q4 report draft", output)
        saved = self.saved_tasks()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["id"], "TASK001")

    def test_add_flow_reprompts_then_succeeds(self):
        output = self.run_cli(["1", "", "T", "", "C", "2026/1/1",
                               "2026-13-45", "2026-11-15", "6"])
        self.assertIn("Task title cannot be empty", output)
        self.assertIn("Task category cannot be empty", output)
        self.assertIn("Invalid date format", output)
        self.assertIn("Invalid date value", output)
        self.assertIn("Task created successfully! Task ID: TASK001",
                      output)
        self.assertEqual(len(self.saved_tasks()), 1)

    def test_add_flow_displays_corruption_message_verbatim(self):
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            f.write("{broken")
        output = self.run_cli(["1", "T", "C", "2026-11-15", "6"])
        self.assertIn("Data file is corrupted, unable to read tasks. "
                      "Please check data/tasks.json.", output)
        # AD-7: still broken, not overwritten.
        with open(storage.DATA_FILE, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{broken")


class TestS303ViewAndStatisticsFlows(CliTestBase):

    def test_view_empty_shows_no_tasks_message(self):
        output = self.run_cli(["2", "6"])
        self.assertIn("No tasks recorded yet.", output)

    def test_view_renders_field_blocks_in_prd_order(self):
        self.saved = None
        tasks = [make_task("TASK001", "alpha"),
                 make_task("TASK002", "beta", completed=True)]
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f)
        output = self.run_cli(["2", "6"])
        self.assertIn("Task ID: TASK001", output)
        self.assertIn("Title: alpha", output)
        self.assertIn("Category: Work", output)
        self.assertIn("Due Date: 2026-11-15", output)
        self.assertIn("Status: Pending", output)
        self.assertIn("Status: Completed", output)
        # Blank line between blocks (PRD FR-3).
        self.assertIn("Status: Pending\n\nTask ID: TASK002", output)
        # Field order within a block.
        self.assertLess(output.index("Task ID: TASK001"),
                        output.index("Title: alpha"))
        self.assertLess(output.index("Due Date: 2026-11-15"),
                        output.index("Status: Pending"))

    def test_view_displays_corruption_message_verbatim(self):
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            f.write("{broken")
        output = self.run_cli(["2", "6"])
        self.assertIn("Data file is corrupted", output)

    def test_statistics_flow_renders_four_lines(self):
        tasks = [make_task("TASK%03d" % i, completed=(i <= 4))
                 for i in range(1, 11)]
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f)
        output = self.run_cli(["5", "6"])
        self.assertIn("Total: 10", output)
        self.assertIn("Pending: 6", output)
        self.assertIn("Completed: 4", output)
        self.assertIn("Completion rate: 40%", output)

    def test_statistics_empty_shows_zeros(self):
        output = self.run_cli(["5", "6"])
        self.assertIn("Total: 0", output)
        self.assertIn("Completion rate: 0%", output)


class TestS304CompleteAndDeleteFlows(CliTestBase):

    def setUp(self):
        super().setUp()
        self.tasks = [make_task("TASK001"), make_task("TASK002"),
                      make_task("TASK003")]
        os.makedirs(storage.DATA_DIR, exist_ok=True)
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f)

    def test_complete_flow_success(self):
        output = self.run_cli(["3", "TASK001", "6"])
        self.assertIn("Task TASK001 marked as complete!", output)
        self.assertIs(self.saved_tasks()[0]["completed"], True)

    def test_complete_flow_already_completed(self):
        tasks = self.saved_tasks()
        tasks[0]["completed"] = True
        with open(storage.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f)
        output = self.run_cli(["3", "TASK001", "6"])
        self.assertIn("Task TASK001 is already completed.", output)

    def test_complete_flow_not_found(self):
        output = self.run_cli(["3", "TASK999", "6"])
        self.assertIn("Task not found, please check the Task ID.", output)

    def test_delete_flow_not_found_short_circuits_no_confirmation(self):
        out = io.StringIO()
        with mock.patch("builtins.input",
                        side_effect=["4", "TASK999", "6"]) as fake_input, \
                contextlib.redirect_stdout(out):
            cli.run()
        # Confirmation prompt was never shown (short-circuit).
        prompts = [c.args[0] for c in fake_input.call_args_list
                   if c.args]
        self.assertNotIn("Are you sure you want to delete this task? (y/n)",
                         prompts)
        self.assertIn("Task not found.", out.getvalue())
        self.assertEqual(len(self.saved_tasks()), 3)

    def test_delete_flow_confirm_y_deletes(self):
        out = io.StringIO()
        with mock.patch("builtins.input",
                        side_effect=["4", "TASK002", "y", "6"]) as fake_input, \
                contextlib.redirect_stdout(out):
            cli.run()
        # Confirmation prompt was asked (mocked input swallows the prompt
        # text, so assert it via the recorded call args, not stdout).
        prompts = [c.args[0] for c in fake_input.call_args_list if c.args]
        self.assertIn("Are you sure you want to delete this task? (y/n)",
                      prompts)
        self.assertIn("Task TASK002 deleted successfully!", out.getvalue())
        self.assertEqual([t["id"] for t in self.saved_tasks()],
                         ["TASK001", "TASK003"])

    def test_delete_flow_confirm_n_cancels_untouched(self):
        output = self.run_cli(["4", "TASK002", "n", "6"])
        self.assertIn("Delete operation cancelled.", output)
        self.assertEqual(len(self.saved_tasks()), 3)

    def test_delete_flow_any_other_input_cancels(self):
        for junk in ("", "N", "no", "cancel"):
            output = self.run_cli(["4", "TASK002", junk, "6"])
            self.assertIn("Delete operation cancelled.", output)
        self.assertEqual(len(self.saved_tasks()), 3)  # nothing deleted

    def test_delete_flow_case_insensitive_y(self):
        output = self.run_cli(["4", "TASK002", "Y", "6"])
        self.assertIn("Task TASK002 deleted successfully!", output)


class TestStaticArchitectureRules(unittest.TestCase):
    """Static AD checks on cli.py source (AD-1/AD-3/AD-6 red lines)."""

    def setUp(self):
        src_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "src")
        with open(os.path.join(src_dir, "cli.py"), encoding="utf-8") as f:
            self.source = f.read()

    def test_no_json_import(self):
        self.assertNotIn("import json", self.source)

    def test_no_bare_except(self):
        for i, line in enumerate(self.source.splitlines(), 1):
            stripped = line.strip()
            self.assertFalse(
                stripped.startswith("except:") or stripped == "except:",
                "bare except at cli.py line %d" % i)

    def test_no_direct_storage_import(self):
        # AD-1: cli talks only to task_manager.
        self.assertNotIn("import storage", self.source)
        self.assertIn("import task_manager", self.source)

    def test_never_prints_raw_exception(self):
        # AD-6: no traceback printing / exception interpolation in cli.
        self.assertNotIn("traceback", self.source.lower())


if __name__ == "__main__":
    unittest.main()
