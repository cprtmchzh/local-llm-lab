import io
import unittest
from unittest.mock import patch

from cli.client import OllamaClient


class FakeResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines

    def __enter__(self):
        return iter(self.lines)

    def __exit__(self, *_args):
        return False


class ClientTests(unittest.TestCase):
    def test_streaming_chat_collects_text_and_stats(self) -> None:
        response = FakeResponse([
            b'{"message":{"content":"hello "},"done":false}\n',
            b'{"message":{"content":"world"},"done":false}\n',
            b'{"done":true,"prompt_eval_count":3,"eval_count":2,"eval_duration":1000000000,"total_duration":2000000000}\n',
        ])
        chunks: list[str] = []
        with patch("urllib.request.urlopen", return_value=response):
            result = OllamaClient("http://127.0.0.1:11434").chat(
                model="test", messages=[{"role": "user", "content": "hi"}],
                context_length=1024, temperature=0.2, on_token=chunks.append,
            )
        self.assertEqual(result.text, "hello world")
        self.assertEqual(chunks, ["hello ", "world"])
        self.assertEqual(result.stats.output_tokens, 2)
        self.assertEqual(result.stats.tokens_per_second, 2.0)


if __name__ == "__main__":
    unittest.main()
