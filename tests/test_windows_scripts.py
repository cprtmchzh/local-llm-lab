import base64
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsScriptTests(unittest.TestCase):
    def test_first_model_validation_script_is_powershell_5_ascii_safe(self) -> None:
        content = (ROOT / "scripts" / "windows" / "verify_first_model.ps1").read_bytes()
        self.assertTrue(content.isascii())

        encoded_prompts = re.findall(rb'FromBase64String\("([A-Za-z0-9+/=]+)"\)', content)
        prompts = [base64.b64decode(value).decode("utf-8") for value in encoded_prompts]
        self.assertEqual(len(prompts), 2)
        self.assertIn("한 문장", prompts[0])
        self.assertIn("Python으로", prompts[1])

    def test_benchmark_uses_noninteractive_docker_config(self) -> None:
        content = (ROOT / "scripts" / "windows" / "run_benchmark.ps1").read_text()

        self.assertIn("docker context inspect", content)
        self.assertIn('$env:DOCKER_CONFIG = $TempDockerConfig', content)
        self.assertIn('$env:DOCKER_HOST = $DockerHost', content)
        self.assertIn('Remove-Item -Recurse -Force $TempDockerConfig', content)


if __name__ == "__main__":
    unittest.main()
