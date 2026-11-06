"""S-401 acceptance tests for main.py (program entry point).

Run from the project root:
    python -m unittest discover -s tests -v
"""

import io
import os
import sys
import unittest
from unittest import mock
from contextlib import redirect_stdout

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

import main  # noqa: E402


class TestS401EntryPoint(unittest.TestCase):

    def test_main_calls_cli_run_and_nothing_else(self):
        # Contract: main() -> cli.run(), nothing else.
        with mock.patch("cli.run") as fake_run:
            main.main()
        self.assertEqual(fake_run.call_count, 1)
        self.assertEqual(fake_run.call_args, mock.call())

    def test_main_imports_only_cli_from_project(self):
        # AD-1: main.py imports cli.py only — static source check.
        src_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "src")
        with open(os.path.join(src_dir, "main.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertIn("import cli", source)
        self.assertNotIn("import task_manager", source)
        self.assertNotIn("import storage", source)
        self.assertNotIn("import json", source)

    def test_main_has_no_business_logic(self):
        # main() body must be a single delegation (no try/except, no I/O).
        import inspect
        source = inspect.getsource(main.main)
        body = [l.strip() for l in source.splitlines()
                if l.strip() and not l.strip().startswith(('"""', "#"))]
        body = body[1:]  # drop the def line
        self.assertEqual(
            [l for l in body if not l.startswith('"""') and l != ''],
            ["cli.run()"])


if __name__ == "__main__":
    unittest.main()
