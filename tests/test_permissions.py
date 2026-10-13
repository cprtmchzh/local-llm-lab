import tempfile
import unittest
from pathlib import Path

from agent.permissions import Decision, PermissionPolicy


class PermissionTests(unittest.TestCase):
    def test_safe_test_command_is_allowed(self) -> None:
        policy = PermissionPolicy(Path.cwd())
        self.assertEqual(policy.command("python -m unittest").decision, Decision.ALLOW)

    def test_network_requires_approval(self) -> None:
        policy = PermissionPolicy(Path.cwd())
        self.assertEqual(policy.command("curl https://example.com").decision, Decision.ASK)

    def test_destructive_command_is_denied(self) -> None:
        policy = PermissionPolicy(Path.cwd())
        self.assertEqual(policy.command("rm -rf build").decision, Decision.DENY)

    def test_inline_python_requires_approval(self) -> None:
        policy = PermissionPolicy(Path.cwd())
        self.assertEqual(policy.command("python -c print(1)").decision, Decision.ASK)

    def test_external_path_is_denied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = PermissionPolicy(root)
            self.assertEqual(policy.path(root.parent / "secret").decision, Decision.DENY)


if __name__ == "__main__":
    unittest.main()
