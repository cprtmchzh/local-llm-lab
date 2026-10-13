import tempfile
import unittest
from pathlib import Path

from agent.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def test_write_requires_explicit_permission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            with self.assertRaises(PermissionError):
                workspace.write_file("sample.txt", "value")

    def test_write_and_read_stay_in_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory), allow_write=True)
            workspace.write_file("nested/sample.txt", "value")
            self.assertEqual(workspace.read_file("nested/sample.txt"), "value")
            with self.assertRaises(PermissionError):
                workspace.read_file("../outside.txt")

    def test_list_pattern_cannot_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            with self.assertRaises(PermissionError):
                workspace.list_files("../**/*")


if __name__ == "__main__":
    unittest.main()
