import json
import shutil
import tempfile
import unittest
from pathlib import Path

from benchmark.evidence import EvidenceError, validate_manifest, verify_bundle
from cli.config import ROOT


class EvidenceTests(unittest.TestCase):
    def test_committed_review_bundle_recomputes(self) -> None:
        summary = verify_bundle(ROOT / "review_bundle")
        self.assertEqual(summary["rows"], 180)
        self.assertEqual(summary["pairs"], 60)

    def test_manifest_hash_mismatch_is_rejected(self) -> None:
        source = ROOT / "review_bundle"
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            shutil.copyfile(source / "raw_results.jsonl", bundle / "raw_results.jsonl")
            manifest = json.loads((source / "evidence_manifest.json").read_text(encoding="utf-8"))
            manifest["raw_results"]["sha256"] = "0" * 64
            (bundle / "evidence_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(EvidenceError, "raw SHA-256 mismatch"):
                validate_manifest(bundle)


if __name__ == "__main__":
    unittest.main()
