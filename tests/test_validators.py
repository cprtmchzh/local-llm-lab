import unittest

from benchmark.validators import validate_clamp, validate_tool_json


class ValidatorTests(unittest.TestCase):
    def test_clamp_behavior(self) -> None:
        score, _ = validate_clamp("def clamp(value, low, high):\n    if low > high:\n        raise ValueError()\n    return min(max(value, low), high)")
        self.assertEqual(score, 100)

    def test_clamp_rejects_import(self) -> None:
        score, _ = validate_clamp("import os\ndef clamp(value, low, high):\n    return value")
        self.assertEqual(score, 0)

    def test_tool_json_is_structural(self) -> None:
        expected = {"tool": "run_tests", "args": {"command": "python -m unittest"}}
        self.assertEqual(validate_tool_json(json_text := '{"tool":"run_tests","args":{"command":"python -m unittest"}}', expected)[0], 100)
        self.assertTrue(json_text)


if __name__ == "__main__":
    unittest.main()
