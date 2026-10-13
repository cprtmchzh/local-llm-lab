import json
import tempfile
import unittest
from pathlib import Path

from cli.config import RuntimeConfig
from cli.model_manager import ModelManager


class ConfigTests(unittest.TestCase):
    def test_default_runtime_is_local(self) -> None:
        config = RuntimeConfig.load()
        self.assertEqual(config.base_url, "http://127.0.0.1:11434")

    def test_remote_runtime_is_rejected(self) -> None:
        value = {
            "base_url": "https://example.com",
            "default_model": "x",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime.yaml"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError):
                RuntimeConfig.load(path)

    def test_model_manifest_has_four_roles(self) -> None:
        manager = ModelManager()
        self.assertEqual(len(manager.models), 4)
        self.assertEqual(manager.get("general_base").runtime_name, "qwen3:8b")


if __name__ == "__main__":
    unittest.main()
