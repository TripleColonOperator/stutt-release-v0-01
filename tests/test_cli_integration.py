"""Exercise the distributed CLI in child processes with no model service."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
RELEASE_FILES = (
    "stutt_command_path.py",
    "stutt_model_adapter.py",
    "stutt_model_backends.example.json",
    "README.md",
    "REUBARB_STUTT_ROADMAP.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    ".gitignore",
)


class StandaloneCliTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = tempfile.TemporaryDirectory(prefix="stutt-release-test-")
        self.addCleanup(fixture.cleanup)
        self.root = Path(fixture.name)
        self.package = self.root / "STUTT Release With Spaces"
        self.package.mkdir()
        for name in RELEASE_FILES:
            shutil.copy2(PACKAGE / name, self.package / name)
        # Only operating-system essentials are inherited, never model credentials.
        self.environment = {
            key: os.environ[key]
            for key in ("SystemRoot", "WINDIR", "TEMP", "TMP")
            if key in os.environ
        }
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")

    def run_cli(self, *arguments: str, stdin: str | None = None):
        return subprocess.run(
            [sys.executable, "-B", str(self.package / "stutt_command_path.py"), *arguments],
            cwd=self.root,
            env=self.environment,
            input=stdin,
            capture_output=True,
            encoding="utf-8",
            timeout=10,
        )

    def test_readme_quickstart_works_from_an_unrelated_directory(self) -> None:
        cases = (
            ("status", "STUTT command path active."),
            ("commands", "echo <text>"),
            ("echo Hello, STUTT", "Hello, STUTT\n"),
            ("count Sample text", '"characters": 11'),
            ("json [1,2,3]", "[\n  1,\n  2,\n  3\n]"),
            ("list-files", "README.md"),
        )
        before = {p.relative_to(self.package): p.read_bytes() for p in self.package.rglob("*") if p.is_file()}
        for command, expected in cases:
            with self.subTest(command=command):
                result = self.run_cli("--input", command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
                self.assertEqual(result.stderr, "")
        after = {p.relative_to(self.package): p.read_bytes() for p in self.package.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_unicode_json_and_payload_survive_actual_process_arguments(self) -> None:
        result = self.run_cli("--input", 'json {"CaseSensitive": "世界", "Bool": true}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"CaseSensitive": "世界", "Bool": True})
        result = self.run_cli("--input", "echo  MiXeD 世界  ")
        self.assertEqual(result.stdout, " MiXeD 世界  \n")

    def test_document_commands_use_copied_release_documents(self) -> None:
        for command, expected in (("readme", "# STUTT"), ("roadmap", "# Reubarb Pi, STUTT")):
            with self.subTest(command=command):
                result = self.run_cli("--input", command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)

    def test_backend_inventory_uses_bundled_config_without_connecting(self) -> None:
        result = self.run_cli("--input", "model-backends")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("localhost:8000", result.stdout)
        self.assertNotIn("nvidia-cloud-nim", result.stdout)

    def test_invalid_input_and_traversal_return_errors_without_tracebacks(self) -> None:
        for command in ('json {"Incomplete":', "json NaN", "list-files ..", "list-files missing-directory"):
            with self.subTest(command=command):
                result = self.run_cli("--input", command)
                self.assertEqual(result.returncode, 1)
                self.assertIn("error:", result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_interactive_pipe_preserves_text_and_handles_eof(self) -> None:
        result = self.run_cli(stdin="echo MiXeD  \nexit\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MiXeD  \n", result.stdout)
        result = self.run_cli(stdin="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_and_disabled_configs_fail_before_network_access(self) -> None:
        config = self.root / "broken.json"
        for contents in ("{", '{"openai_compatible": []}'):
            with self.subTest(contents=contents):
                config.write_text(contents, encoding="utf-8")
                result = self.run_cli("--model", "--config", "broken.json", "--input", "a free form request")
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_missing_bundled_config_has_clear_failure_from_other_cwd(self) -> None:
        # This is an owned temporary fixture, not the user's release configuration.
        (self.package / "stutt_model_backends.example.json").rename(self.package / "example-backup.json")
        result = self.run_cli("--input", "model-backends")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_optional_assets_report_absence_without_crashing(self) -> None:
        for command in ("font", "glyphs", "check-glyph-map"):
            with self.subTest(command=command):
                result = self.run_cli("--input", command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("not found", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
